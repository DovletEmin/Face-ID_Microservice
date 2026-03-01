"""Depth-based anti-spoofing analysis.

Uses the Intel RealSense D415 depth data to verify
that the detected face is a real 3D object and not a
photo, screen, or mask.
"""

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class AntiSpoofAnalyzer:
    """Analyzes depth data to detect face spoofing attempts."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def analyze(
        self,
        depth_roi: Optional[np.ndarray],
        face_bbox: list,
    ) -> Tuple[bool, float, bool]:
        """Perform anti-spoofing analysis on a face region.

        Combines multiple checks:
        1. Depth map validity
        2. 3D structure verification (face curvature)
        3. Edge depth consistency

        Args:
            depth_roi: Depth data for face region (meters, float32).
            face_bbox: Face bounding box [x1, y1, x2, y2].

        Returns:
            Tuple of (is_real, confidence, depth_verified).
        """
        # If no depth data, cannot verify — assume unknown
        if depth_roi is None or depth_roi.size == 0:
            logger.warning("No depth data for anti-spoof check.")
            return True, 0.5, False

        checks = []

        # Check 1: Depth coverage
        coverage_ok, coverage_score = self._check_depth_coverage(depth_roi)
        checks.append(("coverage", coverage_ok, coverage_score))

        # Check 2: 3D structure (nose protrusion)
        structure_ok, structure_score = self._check_3d_structure(depth_roi)
        checks.append(("structure", structure_ok, structure_score))

        # Check 3: Depth gradient (smooth transitions = real face)
        gradient_ok, gradient_score = self._check_depth_gradient(depth_roi)
        checks.append(("gradient", gradient_ok, gradient_score))

        # Check 4: Face depth range
        range_ok, range_score = self._check_depth_range(depth_roi)
        checks.append(("range", range_ok, range_score))

        # Aggregate results
        total_score = sum(s for _, _, s in checks) / len(checks)
        all_passed = all(ok for _, ok, _ in checks)

        is_real = total_score >= self._settings.anti_spoof_threshold
        depth_verified = True

        logger.info(
            f"Anti-spoof: real={is_real}, score={total_score:.3f}, "
            f"checks={[(n, ok, f'{s:.2f}') for n, ok, s in checks]}"
        )

        return is_real, total_score, depth_verified

    def _check_depth_coverage(
        self, depth_roi: np.ndarray
    ) -> Tuple[bool, float]:
        """Check that sufficient depth pixels are valid."""
        valid_mask = (depth_roi > 0.1) & (depth_roi < 1.5)
        ratio = np.sum(valid_mask) / depth_roi.size

        # At least 40% of the face region should have valid depth
        return ratio >= 0.4, min(1.0, ratio / 0.7)

    def _check_3d_structure(
        self, depth_roi: np.ndarray
    ) -> Tuple[bool, float]:
        """Check for 3D facial structure (nose protrusion).

        A real face has the center (nose area) closer to the camera
        than the edges (cheeks, forehead).
        """
        h, w = depth_roi.shape[:2]
        if h < 20 or w < 20:
            return True, 0.5

        valid_mask = (depth_roi > 0.1) & (depth_roi < 1.5)

        # Central region (nose area)
        ch, cw = h // 4, w // 4
        center = depth_roi[ch : 3 * ch, cw : 3 * cw]
        center_valid = center[(center > 0.1) & (center < 1.5)]

        # Edge region
        edge_mask = np.ones_like(depth_roi, dtype=bool)
        edge_mask[ch : 3 * ch, cw : 3 * cw] = False
        edge = depth_roi[edge_mask & valid_mask]

        if len(center_valid) < 10 or len(edge) < 10:
            return True, 0.5

        center_mean = np.mean(center_valid)
        edge_mean = np.mean(edge)

        # Nose should be 1-6cm closer than edges
        protrusion = (edge_mean - center_mean) * 100  # Convert to cm

        if protrusion < 0.5:
            return False, 0.2  # Flat or inverted = likely spoof
        if protrusion > 10:
            return False, 0.3  # Too much protrusion = likely spoof

        # Optimal protrusion is ~2-4cm
        score = min(1.0, protrusion / 3.0) if protrusion <= 4.0 else max(0.3, 1.0 - (protrusion - 4.0) / 6.0)
        return protrusion >= 0.5, score

    def _check_depth_gradient(
        self, depth_roi: np.ndarray
    ) -> Tuple[bool, float]:
        """Check depth gradient smoothness.

        Real faces have smooth depth gradients.
        Photos/screens have flat or noisy depth.
        """
        valid_mask = (depth_roi > 0.1) & (depth_roi < 1.5)
        if np.sum(valid_mask) < 100:
            return True, 0.5

        # Compute gradients
        depth_filled = depth_roi.copy()
        depth_filled[~valid_mask] = np.median(depth_roi[valid_mask])

        grad_x = cv2.Sobel(depth_filled, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(depth_filled, cv2.CV_32F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(grad_x**2 + grad_y**2)

        mean_grad = np.mean(gradient_mag[valid_mask])
        std_grad = np.std(gradient_mag[valid_mask])

        # Real face has moderate gradient (not flat, not noisy)
        if mean_grad < 0.001:
            return False, 0.2  # Too flat
        if std_grad > 0.05:
            return False, 0.3  # Too noisy

        score = min(1.0, mean_grad / 0.005)
        return True, score

    def _check_depth_range(
        self, depth_roi: np.ndarray
    ) -> Tuple[bool, float]:
        """Check that face depth is within expected range."""
        valid = depth_roi[(depth_roi > 0.1) & (depth_roi < 2.0)]
        if len(valid) < 10:
            return True, 0.5

        mean_depth = np.mean(valid)
        depth_range = np.max(valid) - np.min(valid)

        # Face should be 20cm - 1.2m away
        distance_ok = 0.2 <= mean_depth <= 1.2

        # Face depth range should be 1-15cm
        range_cm = depth_range * 100
        range_ok = 1.0 <= range_cm <= 15.0

        if not distance_ok:
            return False, 0.2
        if not range_ok:
            return False, 0.3

        score = 0.5 + 0.25 * min(1.0, range_cm / 4.0) + 0.25 * (1.0 if distance_ok else 0.0)
        return True, min(1.0, score)
