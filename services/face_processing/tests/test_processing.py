"""Face processing service tests."""

import numpy as np
import pytest

from app.processing.anti_spoof import AntiSpoofAnalyzer
from app.processing.matcher import FaceMatcher


class TestAntiSpoof:
    """Tests for anti-spoofing analyzer."""

    def setup_method(self):
        self.analyzer = AntiSpoofAnalyzer()

    def test_real_face_passes(self):
        """Real 3D face depth should pass anti-spoofing."""
        # Simulate real face: center closer, edges farther
        depth_roi = np.random.uniform(0.42, 0.46, (120, 100)).astype(np.float32)
        depth_roi[30:90, 25:75] -= 0.03  # Nose protrusion

        is_real, confidence, depth_verified = self.analyzer.analyze(
            depth_roi, [0, 0, 100, 120]
        )
        assert is_real is True
        assert confidence > 0.4

    def test_flat_surface_fails(self):
        """Flat surface (photo) should fail anti-spoofing."""
        depth_roi = np.full((120, 100), 0.5, dtype=np.float32)
        depth_roi += np.random.normal(0, 0.0005, depth_roi.shape).astype(np.float32)

        is_real, confidence, _ = self.analyzer.analyze(
            depth_roi, [0, 0, 100, 120]
        )
        assert is_real is False

    def test_no_depth_returns_unknown(self):
        """No depth data should return True with low confidence."""
        is_real, confidence, depth_verified = self.analyzer.analyze(
            None, [0, 0, 100, 120]
        )
        assert is_real is True
        assert depth_verified is False


class TestFaceMatcher:
    """Tests for face matching logic."""

    def setup_method(self):
        self.matcher = FaceMatcher()

    def test_compare_identical(self):
        """Identical embeddings should have similarity ~1.0."""
        emb = np.random.randn(512).astype(np.float32)
        emb /= np.linalg.norm(emb)
        sim = self.matcher.compare_embeddings(emb, emb)
        assert sim > 0.99

    def test_compare_different(self):
        """Random embeddings should have low similarity."""
        emb1 = np.random.randn(512).astype(np.float32)
        emb2 = np.random.randn(512).astype(np.float32)
        emb1 /= np.linalg.norm(emb1)
        emb2 /= np.linalg.norm(emb2)
        sim = self.matcher.compare_embeddings(emb1, emb2)
        assert sim < 0.5

    def test_depth_signature_match(self):
        """Similar depth signatures should match."""
        sig = [0.4 + 0.01 * i for i in range(64)]
        sig_noisy = [s + np.random.normal(0, 0.003) for s in sig]

        is_match, similarity = self.matcher.compare_depth_signatures(sig, sig_noisy)
        assert is_match is True
        assert similarity > 0.8

    def test_depth_signature_mismatch(self):
        """Very different depth signatures should not match."""
        sig1 = [0.4 + 0.01 * i for i in range(64)]
        sig2 = [0.6 - 0.01 * i for i in range(64)]

        is_match, similarity = self.matcher.compare_depth_signatures(sig1, sig2)
        assert is_match is False
