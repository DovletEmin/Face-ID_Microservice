"""Face embedding extraction using ArcFace (InsightFace).

Produces 512-dimensional face embeddings for recognition.
"""

import logging
from typing import Optional

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class FaceEmbedder:
    """Extracts 512-d face embeddings using ArcFace model."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def extract_embedding(self, face_obj) -> Optional[np.ndarray]:
        """Extract embedding from an InsightFace detected face object.

        The InsightFace library already computes embeddings during
        detection, so we just need to retrieve and normalize them.

        Args:
            face_obj: InsightFace Face object from detection.

        Returns:
            Normalized 512-d embedding vector, or None.
        """
        try:
            embedding = face_obj.normed_embedding
            if embedding is None:
                logger.warning("Face object has no embedding.")
                return None

            # Ensure it's normalized (L2 norm = 1)
            norm = np.linalg.norm(embedding)
            if norm < 1e-6:
                logger.warning("Zero-norm embedding detected.")
                return None

            embedding = embedding / norm
            return embedding.astype(np.float32)

        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None

    def compute_quality_score(self, face_obj, image: np.ndarray) -> float:
        """Compute face quality score for enrollment filtering.

        Higher quality = better enrollment. Considers:
        - Detection confidence
        - Face size relative to image
        - Landmark alignment quality

        Args:
            face_obj: InsightFace Face object.
            image: Source BGR image.

        Returns:
            Quality score between 0.0 and 1.0.
        """
        try:
            score = 0.0

            # Detection confidence (0-1)
            det_score = float(face_obj.det_score)
            score += det_score * 0.4

            # Face size score (larger = better for enrollment)
            bbox = face_obj.bbox.astype(int)
            face_w = bbox[2] - bbox[0]
            face_h = bbox[3] - bbox[1]
            img_h, img_w = image.shape[:2]
            face_ratio = (face_w * face_h) / (img_w * img_h)
            size_score = min(1.0, face_ratio / 0.15)  # 15% of image = max score
            score += size_score * 0.3

            # Landmark symmetry score
            if face_obj.kps is not None and len(face_obj.kps) >= 5:
                kps = face_obj.kps
                # Eye symmetry (left and right eyes should be at similar y)
                eye_dy = abs(kps[0][1] - kps[1][1])
                eye_dist = abs(kps[1][0] - kps[0][0])
                if eye_dist > 0:
                    symmetry = 1.0 - min(1.0, eye_dy / eye_dist)
                    score += symmetry * 0.3

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.warning(f"Quality score computation failed: {e}")
            return 0.5
