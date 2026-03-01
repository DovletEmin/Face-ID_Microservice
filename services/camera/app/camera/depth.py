"""Depth frame processing utilities.

Provides analysis of depth data for face verification,
including depth map statistics and 3D point cloud extraction.
"""

import logging
from typing import Dict, Optional, Tuple

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class DepthProcessor:
    """Processes depth frames for face liveness and 3D analysis."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def compute_depth_stats(
        self, depth_roi: np.ndarray
    ) -> Dict[str, float]:
        """Compute depth statistics for a region of interest.

        Args:
            depth_roi: Depth ROI in meters (float32).

        Returns:
            Dictionary with depth statistics.
        """
        valid_mask = (
            (depth_roi > self._settings.depth_min_distance)
            & (depth_roi < self._settings.depth_max_distance)
        )
        valid_depths = depth_roi[valid_mask]

        if len(valid_depths) == 0:
            return {
                "min_depth": 0.0,
                "max_depth": 0.0,
                "mean_depth": 0.0,
                "std_depth": 0.0,
                "valid_ratio": 0.0,
                "depth_range": 0.0,
            }

        return {
            "min_depth": float(np.min(valid_depths)),
            "max_depth": float(np.max(valid_depths)),
            "mean_depth": float(np.mean(valid_depths)),
            "std_depth": float(np.std(valid_depths)),
            "valid_ratio": float(len(valid_depths) / depth_roi.size),
            "depth_range": float(np.max(valid_depths) - np.min(valid_depths)),
        }

    def extract_depth_signature(
        self, depth_roi: np.ndarray, grid_size: int = 8
    ) -> Optional[list]:
        """Extract a compact depth signature from a face ROI.

        Divides the depth ROI into a grid and computes mean depth
        for each cell. This creates a compact 3D shape descriptor.

        Args:
            depth_roi: Depth ROI in meters.
            grid_size: Grid resolution (grid_size x grid_size).

        Returns:
            Flattened list of grid cell mean depths, or None.
        """
        if depth_roi is None or depth_roi.size == 0:
            return None

        h, w = depth_roi.shape[:2]
        if h < grid_size or w < grid_size:
            return None

        cell_h = h // grid_size
        cell_w = w // grid_size
        signature = []

        for i in range(grid_size):
            for j in range(grid_size):
                cell = depth_roi[
                    i * cell_h : (i + 1) * cell_h,
                    j * cell_w : (j + 1) * cell_w,
                ]
                valid = cell[
                    (cell > self._settings.depth_min_distance)
                    & (cell < self._settings.depth_max_distance)
                ]
                if len(valid) > 0:
                    signature.append(float(np.mean(valid)))
                else:
                    signature.append(0.0)

        return signature

    def check_depth_liveness(
        self, depth_roi: np.ndarray
    ) -> Tuple[bool, float]:
        """Check if the depth ROI represents a real 3D face.

        A real face has:
        - Sufficient depth variation (nose protrudes ~2-4cm from cheeks)
        - Valid depth coverage
        - Depth range within expected bounds for a face

        Args:
            depth_roi: Depth ROI in meters.

        Returns:
            Tuple of (is_live, confidence_score).
        """
        stats = self.compute_depth_stats(depth_roi)

        # Check 1: Sufficient valid depth data
        if stats["valid_ratio"] < 0.3:
            logger.debug(f"Liveness fail: low valid ratio {stats['valid_ratio']:.2f}")
            return False, 0.0

        # Check 2: Depth range should be 1-15cm for a real face
        depth_range_cm = stats["depth_range"] * 100
        if depth_range_cm < 1.0 or depth_range_cm > 20.0:
            logger.debug(
                f"Liveness fail: depth range {depth_range_cm:.1f}cm "
                f"(expected 1-20cm)"
            )
            return False, 0.2

        # Check 3: Standard deviation should indicate 3D structure
        if stats["std_depth"] < 0.005:  # Less than 5mm std = flat surface
            logger.debug(
                f"Liveness fail: low depth std {stats['std_depth']*1000:.1f}mm"
            )
            return False, 0.3

        # Check 4: Face should be within reasonable distance
        if stats["mean_depth"] < 0.15 or stats["mean_depth"] > 1.2:
            logger.debug(
                f"Liveness fail: face distance {stats['mean_depth']:.2f}m"
            )
            return False, 0.2

        # Compute confidence based on how well depth matches expectations
        range_score = min(1.0, depth_range_cm / 4.0)  # Optimal ~4cm
        coverage_score = min(1.0, stats["valid_ratio"] / 0.7)
        std_score = min(1.0, stats["std_depth"] / 0.015)

        confidence = (range_score * 0.4 + coverage_score * 0.3 + std_score * 0.3)
        confidence = max(0.0, min(1.0, confidence))

        is_live = confidence > 0.5
        return is_live, confidence

    def colorize_depth(
        self,
        depth_frame: np.ndarray,
        min_depth_m: float = 0.1,
        max_depth_m: float = 1.5,
    ) -> np.ndarray:
        """Convert depth frame to colorized visualization.

        Args:
            depth_frame: Raw depth frame (uint16, millimeters).
            min_depth_m: Minimum depth in meters for colormap.
            max_depth_m: Maximum depth in meters for colormap.

        Returns:
            Colorized depth frame (uint8, BGR).
        """
        import cv2

        depth_m = depth_frame.astype(np.float32) / 1000.0
        depth_normalized = np.clip(
            (depth_m - min_depth_m) / (max_depth_m - min_depth_m),
            0.0,
            1.0,
        )
        depth_uint8 = (depth_normalized * 255).astype(np.uint8)
        colorized = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_JET)

        # Mark invalid pixels as black
        invalid_mask = (depth_frame == 0) | (depth_m < min_depth_m) | (depth_m > max_depth_m)
        colorized[invalid_mask] = 0

        return colorized
