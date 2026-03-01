"""Face detection using InsightFace.

Uses RetinaFace detector from the InsightFace library for
high-accuracy face detection with landmark localization.
"""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-loaded model
_face_analyzer = None


def _get_analyzer():
    """Lazy-load InsightFace analyzer (heavy model, load once)."""
    global _face_analyzer

    if _face_analyzer is not None:
        return _face_analyzer

    try:
        from insightface.app import FaceAnalysis

        settings = get_settings()
        _face_analyzer = FaceAnalysis(
            name="buffalo_l",
            root=settings.model_cache_dir,
            providers=["CPUExecutionProvider"],
        )
        _face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded successfully.")
        return _face_analyzer

    except Exception as e:
        logger.error(f"Failed to load InsightFace model: {e}")
        return None


class FaceDetector:
    """Detects faces in images using InsightFace RetinaFace."""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def model_loaded(self) -> bool:
        """Check if the detection model is loaded."""
        return _face_analyzer is not None

    def detect_faces(
        self, image: np.ndarray
    ) -> List[dict]:
        """Detect all faces in an image.

        Args:
            image: BGR image as numpy array.

        Returns:
            List of detected faces with bbox, confidence, landmarks.
        """
        analyzer = _get_analyzer()
        if analyzer is None:
            logger.warning("Face analyzer not loaded — returning empty.")
            return []

        try:
            faces = analyzer.get(image)
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []

        results = []
        for face in faces:
            score = float(face.det_score)
            if score < self._settings.face_detection_confidence:
                continue

            bbox = face.bbox.astype(int).tolist()
            landmarks = (
                face.kps.tolist() if face.kps is not None else None
            )

            results.append({
                "bbox": bbox,
                "confidence": score,
                "landmarks": landmarks,
                "face_obj": face,  # Keep for embedding extraction
            })

        # Sort by confidence descending
        results.sort(key=lambda x: x["confidence"], reverse=True)

        logger.debug(f"Detected {len(results)} faces (min conf: {self._settings.face_detection_confidence})")
        return results

    def detect_largest_face(
        self, image: np.ndarray
    ) -> Optional[dict]:
        """Detect the largest face in the image.

        For authentication, we typically want the most prominent face.

        Args:
            image: BGR image.

        Returns:
            Largest face detection dict, or None.
        """
        faces = self.detect_faces(image)
        if not faces:
            return None

        # Select largest face by bounding box area
        def face_area(f: dict) -> int:
            b = f["bbox"]
            return (b[2] - b[0]) * (b[3] - b[1])

        return max(faces, key=face_area)

    def align_face(
        self,
        image: np.ndarray,
        landmarks: List[List[float]],
        output_size: Tuple[int, int] = (112, 112),
    ) -> Optional[np.ndarray]:
        """Align face using detected landmarks.

        Args:
            image: BGR image.
            landmarks: 5-point facial landmarks.
            output_size: Output face size.

        Returns:
            Aligned face image, or None.
        """
        if landmarks is None or len(landmarks) < 5:
            return None

        src_pts = np.array(landmarks[:5], dtype=np.float32)

        # Standard 112x112 alignment target points
        dst_pts = np.array(
            [
                [38.2946, 51.6963],
                [73.5318, 51.5014],
                [56.0252, 71.7366],
                [41.5493, 92.3655],
                [70.7299, 92.2041],
            ],
            dtype=np.float32,
        )

        # Scale target points to output size
        scale_x = output_size[0] / 112.0
        scale_y = output_size[1] / 112.0
        dst_pts[:, 0] *= scale_x
        dst_pts[:, 1] *= scale_y

        M = cv2.estimateAffinePartial2D(src_pts, dst_pts)[0]
        if M is None:
            return None

        aligned = cv2.warpAffine(
            image, M, output_size, borderValue=(0, 0, 0)
        )
        return aligned
