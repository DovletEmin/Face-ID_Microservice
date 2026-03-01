"""Utility functions for camera/depth data shared by face processing routes."""

import numpy as np
from typing import Optional


def extract_depth_signature(
    depth_roi: np.ndarray, grid_size: int = 8
) -> Optional[list]:
    """Extract a compact depth signature from a face depth ROI.

    Args:
        depth_roi: Depth ROI in meters (float32).
        grid_size: Grid resolution.

    Returns:
        Flattened list of grid cell mean depths.
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
            valid = cell[(cell > 0.1) & (cell < 1.5)]
            if len(valid) > 0:
                signature.append(float(np.mean(valid)))
            else:
                signature.append(0.0)

    return signature
