"""Face matching against enrolled faces using pgvector similarity search."""

import logging
from typing import Optional, Tuple

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class FaceMatcher:
    """Matches face embeddings against enrolled faces in PostgreSQL + pgvector."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def find_match(
        self, embedding: np.ndarray, db_session
    ) -> Optional[dict]:
        """Find the best matching enrolled face for a given embedding.

        Uses pgvector cosine similarity search for efficient matching.

        Args:
            embedding: 512-d face embedding vector.
            db_session: AsyncSession for database access.

        Returns:
            Match result dict or None if no match found.
        """
        from sqlalchemy import text

        threshold = self._settings.face_recognition_threshold
        embedding_list = embedding.tolist()

        try:
            # pgvector cosine distance: 1 - cosine_similarity
            # Lower distance = more similar
            query = text("""
                SELECT 
                    fe.id,
                    fe.user_id,
                    u.username,
                    u.full_name,
                    1 - (fe.embedding <=> :embedding::vector) AS similarity,
                    fe.depth_signature
                FROM face_enrollments fe
                JOIN users u ON u.id = fe.user_id
                WHERE u.is_active = true
                ORDER BY fe.embedding <=> :embedding::vector
                LIMIT 1
            """)

            result = await db_session.execute(
                query, {"embedding": str(embedding_list)}
            )
            row = result.fetchone()

            if row is None:
                logger.debug("No enrolled faces found.")
                return None

            similarity = float(row.similarity)

            if similarity < threshold:
                logger.debug(
                    f"Best match similarity {similarity:.4f} "
                    f"below threshold {threshold}"
                )
                return None

            logger.info(
                f"Face matched: user={row.username}, "
                f"similarity={similarity:.4f}"
            )

            return {
                "enrollment_id": str(row.id),
                "user_id": str(row.user_id),
                "username": row.username,
                "full_name": row.full_name,
                "similarity": similarity,
                "depth_signature": row.depth_signature,
            }

        except Exception as e:
            logger.error(f"Face matching query failed: {e}")
            return None

    def compare_embeddings(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First 512-d embedding.
            embedding2: Second 512-d embedding.

        Returns:
            Cosine similarity (0.0 - 1.0).
        """
        dot = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(dot / (norm1 * norm2))

    def compare_depth_signatures(
        self,
        sig1: list,
        sig2: list,
        tolerance: float = 0.02,
    ) -> Tuple[bool, float]:
        """Compare two depth signatures for 3D face verification.

        This adds an extra layer of security beyond 2D embedding match.

        Args:
            sig1: Enrolled depth signature.
            sig2: Current depth signature.
            tolerance: Maximum average depth difference in meters.

        Returns:
            Tuple of (is_match, similarity).
        """
        if not sig1 or not sig2:
            return True, 0.5  # No depth data — skip check

        if len(sig1) != len(sig2):
            return False, 0.0

        arr1 = np.array(sig1, dtype=np.float32)
        arr2 = np.array(sig2, dtype=np.float32)

        # Filter out zero values (invalid depth cells)
        valid_mask = (arr1 > 0) & (arr2 > 0)
        if np.sum(valid_mask) < len(sig1) * 0.3:
            return True, 0.5  # Insufficient depth data

        valid1 = arr1[valid_mask]
        valid2 = arr2[valid_mask]

        # Normalize to relative depths (remove absolute distance influence)
        valid1 = valid1 - np.mean(valid1)
        valid2 = valid2 - np.mean(valid2)

        # Compute correlation
        if np.std(valid1) < 1e-6 or np.std(valid2) < 1e-6:
            return True, 0.5

        correlation = float(np.corrcoef(valid1, valid2)[0, 1])
        similarity = max(0.0, correlation)

        is_match = similarity > 0.6
        return is_match, similarity
