"""Camera service tests."""

import numpy as np
import pytest

from app.camera.depth import DepthProcessor


class TestDepthProcessor:
    """Tests for depth processing logic."""

    def setup_method(self):
        self.processor = DepthProcessor()

    def test_compute_depth_stats_valid(self):
        """Valid depth ROI returns correct statistics."""
        # Simulate face depth: 0.4-0.45m range
        depth_roi = np.random.uniform(0.40, 0.45, (100, 80)).astype(np.float32)
        stats = self.processor.compute_depth_stats(depth_roi)

        assert stats["valid_ratio"] > 0.9
        assert 0.39 < stats["min_depth"] < 0.46
        assert 0.39 < stats["max_depth"] < 0.46
        assert stats["depth_range"] < 0.1

    def test_compute_depth_stats_empty(self):
        """All-zero depth returns zero stats."""
        depth_roi = np.zeros((100, 80), dtype=np.float32)
        stats = self.processor.compute_depth_stats(depth_roi)

        assert stats["valid_ratio"] == 0.0
        assert stats["mean_depth"] == 0.0

    def test_depth_liveness_real_face(self):
        """Real face depth profile passes liveness check."""
        # Simulate nose protruding ~3cm from cheeks
        depth_roi = np.random.uniform(0.42, 0.46, (120, 100)).astype(np.float32)
        # Add nose protrusion
        depth_roi[40:80, 30:70] -= 0.03

        is_live, confidence = self.processor.check_depth_liveness(depth_roi)
        assert is_live is True
        assert confidence > 0.5

    def test_depth_liveness_flat_photo(self):
        """Flat surface (photo) fails liveness check."""
        # Uniform depth = flat surface
        depth_roi = np.full((120, 100), 0.5, dtype=np.float32)
        # Add minimal noise
        depth_roi += np.random.normal(0, 0.001, depth_roi.shape).astype(np.float32)

        is_live, confidence = self.processor.check_depth_liveness(depth_roi)
        assert is_live is False
        assert confidence < 0.5

    def test_extract_depth_signature(self):
        """Depth signature has correct size."""
        depth_roi = np.random.uniform(0.3, 0.5, (64, 64)).astype(np.float32)
        signature = self.processor.extract_depth_signature(depth_roi, grid_size=8)

        assert signature is not None
        assert len(signature) == 64  # 8x8 grid

    def test_extract_depth_signature_too_small(self):
        """Too-small ROI returns None."""
        depth_roi = np.random.uniform(0.3, 0.5, (4, 4)).astype(np.float32)
        signature = self.processor.extract_depth_signature(depth_roi, grid_size=8)
        assert signature is None
