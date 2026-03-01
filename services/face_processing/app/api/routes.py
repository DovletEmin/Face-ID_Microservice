"""Face Processing service REST API routes.

Endpoints for face enrollment, authentication, and management.
"""

import base64
import json
import logging
import uuid

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face import get_db_session
from app.camera_utils import extract_depth_signature
from app.processing.detector import FaceDetector
from app.processing.embedder import FaceEmbedder
from app.processing.matcher import FaceMatcher
from app.processing.anti_spoof import AntiSpoofAnalyzer
from app.schemas import (
    EnrollRequest,
    EnrollResponse,
    AuthenticateRequest,
    AuthenticateResponse,
    AntiSpoofResult,
    HealthResponse,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/face", tags=["face"])

# Service instances
detector = FaceDetector()
embedder = FaceEmbedder()
matcher = FaceMatcher()
anti_spoof = AntiSpoofAnalyzer()


def _decode_color_frame(b64_data: str) -> np.ndarray:
    """Decode base64 JPEG to BGR numpy array."""
    img_bytes = base64.b64decode(b64_data)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image")
    return image


def _decode_depth_frame(
    b64_data: str, shape: list
) -> np.ndarray:
    """Decode base64 raw depth data to numpy array."""
    raw_bytes = base64.b64decode(b64_data)
    depth = np.frombuffer(raw_bytes, dtype=np.uint16).reshape(shape)
    return depth


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Face processing service health check."""
    return HealthResponse(
        status="ok",
        service="face-service",
        model_loaded=detector.model_loaded,
    )


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_face(
    request: EnrollRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Enroll a new face for a user.

    Captures the face embedding and depth signature for future authentication.
    Requires a clear frontal face image with depth data.
    """
    try:
        # 1. Decode color frame
        image = _decode_color_frame(request.color_frame_b64)

        # 2. Detect face
        face = detector.detect_largest_face(image)
        if face is None:
            return EnrollResponse(
                success=False,
                message="No face detected. Please look directly at the camera.",
            )

        # 3. Extract embedding
        face_obj = face["face_obj"]
        embedding = embedder.extract_embedding(face_obj)
        if embedding is None:
            return EnrollResponse(
                success=False,
                message="Failed to extract face features. Please try again.",
            )

        # 4. Compute quality score
        quality = embedder.compute_quality_score(face_obj, image)
        if quality < 0.4:
            return EnrollResponse(
                success=False,
                message=f"Face quality too low ({quality:.2f}). "
                "Please ensure good lighting and face the camera directly.",
                quality_score=quality,
            )

        # 5. Process depth data for anti-spoofing
        depth_signature = {}
        if request.depth_data_b64 and request.depth_shape:
            depth_frame = _decode_depth_frame(
                request.depth_data_b64, request.depth_shape
            )
            bbox = face["bbox"]
            depth_roi = depth_frame[
                bbox[1] : bbox[3], bbox[0] : bbox[2]
            ].astype(np.float32) / 1000.0

            # Anti-spoof check during enrollment
            is_real, spoof_conf, _ = anti_spoof.analyze(depth_roi, bbox)
            if not is_real:
                return EnrollResponse(
                    success=False,
                    message="Anti-spoofing check failed. "
                    "Please use your real face.",
                    quality_score=quality,
                )

            # Extract depth signature for future matching
            depth_signature = {
                "grid": extract_depth_signature(depth_roi),
                "stats": _compute_depth_stats(depth_roi),
            }

        # 6. Create or get user
        existing_user = await db.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": request.username},
        )
        user_row = existing_user.fetchone()

        if user_row:
            user_id = user_row.id
        else:
            user_id = uuid.uuid4()
            await db.execute(
                text(
                    "INSERT INTO users (id, username, full_name) "
                    "VALUES (:id, :username, :full_name)"
                ),
                {
                    "id": user_id,
                    "username": request.username,
                    "full_name": request.full_name,
                },
            )

        # 7. Store face enrollment
        enrollment_id = uuid.uuid4()
        embedding_list = embedding.tolist()

        await db.execute(
            text(
                "INSERT INTO face_enrollments "
                "(id, user_id, embedding, depth_signature, quality_score, is_primary) "
                "VALUES (:id, :user_id, :embedding::vector, :depth_sig, :quality, true)"
            ),
            {
                "id": enrollment_id,
                "user_id": user_id,
                "embedding": str(embedding_list),
                "depth_sig": json.dumps(depth_signature) if depth_signature else "{}",
                "quality": quality,
            },
        )

        await db.commit()

        logger.info(
            f"Face enrolled: user={request.username}, "
            f"quality={quality:.2f}"
        )

        return EnrollResponse(
            success=True,
            user_id=str(user_id),
            message="Face enrolled successfully.",
            quality_score=quality,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Enrollment failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Face enrollment failed. Please try again.",
        )


@router.post("/authenticate", response_model=AuthenticateResponse)
async def authenticate_face(
    request: AuthenticateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Authenticate a user by their face.

    Performs face detection, embedding extraction, matching,
    and anti-spoofing verification.
    """
    try:
        # 1. Decode color frame
        image = _decode_color_frame(request.color_frame_b64)

        # 2. Detect face
        face = detector.detect_largest_face(image)
        if face is None:
            return AuthenticateResponse(
                authenticated=False,
                message="No face detected.",
            )

        # 3. Extract embedding
        face_obj = face["face_obj"]
        embedding = embedder.extract_embedding(face_obj)
        if embedding is None:
            return AuthenticateResponse(
                authenticated=False,
                message="Failed to extract face features.",
            )

        # 4. Anti-spoofing check
        spoof_result = AntiSpoofResult(
            is_real=True, confidence=0.5, depth_verified=False, method="none"
        )

        depth_roi = None
        if request.depth_data_b64 and request.depth_shape:
            depth_frame = _decode_depth_frame(
                request.depth_data_b64, request.depth_shape
            )
            bbox = face["bbox"]
            depth_roi = depth_frame[
                bbox[1] : bbox[3], bbox[0] : bbox[2]
            ].astype(np.float32) / 1000.0

            is_real, spoof_conf, depth_verified = anti_spoof.analyze(
                depth_roi, bbox
            )
            spoof_result = AntiSpoofResult(
                is_real=is_real,
                confidence=spoof_conf,
                depth_verified=depth_verified,
                method="depth_analysis",
            )

            if not is_real:
                # Log failed attempt
                await _log_auth(
                    db, None, "authenticate", False,
                    spoof_conf, depth_verified, spoof_conf
                )

                return AuthenticateResponse(
                    authenticated=False,
                    anti_spoof=spoof_result,
                    message="Anti-spoofing check failed. Real face required.",
                )

        # 5. Match against enrolled faces
        match_result = await matcher.find_match(embedding, db)

        if match_result is None:
            await _log_auth(
                db, None, "authenticate", False, 0.0, False, 0.0
            )
            return AuthenticateResponse(
                authenticated=False,
                anti_spoof=spoof_result,
                message="Face not recognized. Please enroll first.",
            )

        # 6. Optional: verify depth signature
        if depth_roi is not None and match_result.get("depth_signature"):
            enrolled_sig = match_result["depth_signature"]
            if isinstance(enrolled_sig, dict) and "grid" in enrolled_sig:
                current_sig = extract_depth_signature(depth_roi)
                if current_sig and enrolled_sig["grid"]:
                    depth_match, depth_sim = matcher.compare_depth_signatures(
                        enrolled_sig["grid"], current_sig
                    )
                    if not depth_match:
                        logger.warning(
                            f"Depth signature mismatch: sim={depth_sim:.3f}"
                        )

        # 7. Log successful authentication
        await _log_auth(
            db,
            match_result["user_id"],
            "authenticate",
            True,
            match_result["similarity"],
            spoof_result.depth_verified,
            spoof_result.confidence,
        )

        logger.info(
            f"Authentication successful: user={match_result['username']}, "
            f"similarity={match_result['similarity']:.4f}"
        )

        return AuthenticateResponse(
            authenticated=True,
            user_id=match_result["user_id"],
            username=match_result["username"],
            confidence=match_result["similarity"],
            anti_spoof=spoof_result,
            message="Authentication successful.",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed. Please try again.",
        )


@router.get("/users")
async def list_enrolled_users(
    db: AsyncSession = Depends(get_db_session),
):
    """List all enrolled users."""
    result = await db.execute(
        text(
            "SELECT u.id, u.username, u.full_name, u.created_at, "
            "COUNT(fe.id) as enrollment_count "
            "FROM users u "
            "LEFT JOIN face_enrollments fe ON fe.user_id = u.id "
            "WHERE u.is_active = true "
            "GROUP BY u.id "
            "ORDER BY u.created_at DESC"
        )
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "username": row.username,
            "full_name": row.full_name,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "enrollment_count": row.enrollment_count,
        }
        for row in rows
    ]


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a user and their face enrollments."""
    await db.execute(
        text("DELETE FROM face_enrollments WHERE user_id = :uid"),
        {"uid": user_id},
    )
    await db.execute(
        text("UPDATE users SET is_active = false WHERE id = :uid"),
        {"uid": user_id},
    )
    await db.commit()
    return {"message": "User deactivated and enrollments deleted."}


async def _log_auth(
    db: AsyncSession,
    user_id,
    action: str,
    success: bool,
    confidence: float,
    depth_verified: bool,
    anti_spoof_score: float,
) -> None:
    """Log an authentication attempt."""
    try:
        await db.execute(
            text(
                "INSERT INTO auth_logs "
                "(id, user_id, action, success, confidence, depth_verified, anti_spoof_score) "
                "VALUES (:id, :user_id, :action, :success, :confidence, :dv, :as_score)"
            ),
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "action": action,
                "success": success,
                "confidence": confidence,
                "dv": depth_verified,
                "as_score": anti_spoof_score,
            },
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")


def _compute_depth_stats(depth_roi: np.ndarray) -> dict:
    """Compute basic depth statistics."""
    valid = depth_roi[(depth_roi > 0.1) & (depth_roi < 1.5)]
    if len(valid) == 0:
        return {}
    return {
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid)),
    }
