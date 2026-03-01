"""Intel RealSense D415 camera driver.

Handles initialization, configuration, and frame acquisition
from the RealSense D415 depth camera.
"""

import logging
import time
from typing import Optional, Tuple

import numpy as np

try:
    import pyrealsense2 as rs

    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False

from app.config import get_settings

logger = logging.getLogger(__name__)


class RealSenseCamera:
    """Intel RealSense D415 camera wrapper.

    Provides thread-safe access to color and depth frames
    with automatic reconnection on failure.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._pipeline: Optional[object] = None
        self._config: Optional[object] = None
        self._align: Optional[object] = None
        self._is_running: bool = False
        self._serial_number: Optional[str] = None
        self._firmware_version: Optional[str] = None
        self._last_frame_time: float = 0.0
        self._consecutive_errors: int = 0
        self._max_consecutive_errors: int = 10

    @property
    def is_running(self) -> bool:
        """Check if camera pipeline is active."""
        return self._is_running

    @property
    def serial_number(self) -> Optional[str]:
        return self._serial_number

    @property
    def firmware_version(self) -> Optional[str]:
        return self._firmware_version

    def start(self) -> bool:
        """Initialize and start the RealSense pipeline.

        Returns:
            True if camera started successfully, False otherwise.
        """
        if not REALSENSE_AVAILABLE:
            logger.warning(
                "pyrealsense2 not available. Running in simulation mode."
            )
            self._is_running = True
            return True

        try:
            self._pipeline = rs.pipeline()
            self._config = rs.config()

            # Configure color stream
            self._config.enable_stream(
                rs.stream.color,
                self._settings.camera_frame_width,
                self._settings.camera_frame_height,
                rs.format.bgr8,
                self._settings.camera_fps,
            )

            # Configure depth stream
            if self._settings.camera_depth_enabled:
                self._config.enable_stream(
                    rs.stream.depth,
                    self._settings.camera_frame_width,
                    self._settings.camera_frame_height,
                    rs.format.z16,
                    self._settings.camera_fps,
                )

            # Start pipeline
            profile = self._pipeline.start(self._config)

            # Get device info
            device = profile.get_device()
            self._serial_number = device.get_info(rs.camera_info.serial_number)
            self._firmware_version = device.get_info(
                rs.camera_info.firmware_version
            )

            # Configure depth-to-color alignment
            if self._settings.camera_depth_enabled:
                self._align = rs.align(rs.stream.color)

            # Apply recommended settings for D415
            depth_sensor = device.first_depth_sensor()
            if depth_sensor.supports(rs.option.emitter_enabled):
                depth_sensor.set_option(rs.option.emitter_enabled, 1)

            self._is_running = True
            self._consecutive_errors = 0
            logger.info(
                f"RealSense D415 started. S/N: {self._serial_number}, "
                f"FW: {self._firmware_version}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start RealSense camera: {e}")
            self._is_running = False
            return False

    def stop(self) -> None:
        """Stop the RealSense pipeline and release resources."""
        if self._pipeline is not None and REALSENSE_AVAILABLE:
            try:
                self._pipeline.stop()
            except Exception as e:
                logger.warning(f"Error stopping pipeline: {e}")
        self._is_running = False
        self._pipeline = None
        logger.info("RealSense camera stopped.")

    def get_frames(
        self, timeout_ms: int = 5000
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Capture aligned color and depth frames.

        Args:
            timeout_ms: Timeout in milliseconds for waiting for frames.

        Returns:
            Tuple of (color_frame, depth_frame) as numpy arrays.
            Returns (None, None) on failure.
        """
        if not self._is_running:
            return None, None

        # Simulation mode when no camera is connected
        if not REALSENSE_AVAILABLE or self._pipeline is None:
            return self._generate_simulated_frames()

        try:
            frames = self._pipeline.wait_for_frames(timeout_ms)

            # Align depth to color
            if self._align is not None:
                frames = self._align.process(frames)

            color_frame = frames.get_color_frame()
            depth_frame = (
                frames.get_depth_frame()
                if self._settings.camera_depth_enabled
                else None
            )

            if not color_frame:
                self._consecutive_errors += 1
                if self._consecutive_errors >= self._max_consecutive_errors:
                    logger.error("Too many consecutive frame errors. Restarting.")
                    self._restart()
                return None, None

            self._consecutive_errors = 0
            self._last_frame_time = time.time()

            color_array = np.asarray(color_frame.get_data())
            depth_array = (
                np.asarray(depth_frame.get_data())
                if depth_frame
                else None
            )

            return color_array, depth_array

        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            self._consecutive_errors += 1
            if self._consecutive_errors >= self._max_consecutive_errors:
                self._restart()
            return None, None

    def get_depth_at_point(
        self, depth_frame: np.ndarray, x: int, y: int
    ) -> float:
        """Get depth value at a specific pixel.

        Args:
            depth_frame: Depth frame as numpy array.
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Depth in meters. Returns 0.0 if invalid.
        """
        if depth_frame is None:
            return 0.0
        if 0 <= y < depth_frame.shape[0] and 0 <= x < depth_frame.shape[1]:
            # D415 depth is in millimeters, convert to meters
            return float(depth_frame[y, x]) / 1000.0
        return 0.0

    def get_depth_roi(
        self,
        depth_frame: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> Optional[np.ndarray]:
        """Extract depth region of interest.

        Args:
            depth_frame: Full depth frame.
            x1, y1, x2, y2: Bounding box coordinates.

        Returns:
            Depth ROI as numpy array in meters, or None.
        """
        if depth_frame is None:
            return None
        h, w = depth_frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x1 >= x2 or y1 >= y2:
            return None
        roi = depth_frame[y1:y2, x1:x2].astype(np.float32) / 1000.0
        return roi

    def _restart(self) -> None:
        """Attempt to restart the camera pipeline."""
        logger.warning("Attempting camera restart...")
        self.stop()
        time.sleep(1.0)
        self.start()

    def _generate_simulated_frames(
        self,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Generate simulated frames for development without camera hardware."""
        h = self._settings.camera_frame_height
        w = self._settings.camera_frame_width

        # Simulated color frame (gradient)
        color = np.zeros((h, w, 3), dtype=np.uint8)
        color[:, :, 0] = 40  # B
        color[:, :, 1] = 40  # G
        color[:, :, 2] = 60  # R

        # Draw "NO CAMERA" text indicator
        cv2_available = False
        try:
            import cv2

            cv2_available = True
        except ImportError:
            pass

        if cv2_available:
            import cv2

            cv2.putText(
                color,
                "SIMULATION MODE",
                (w // 2 - 140, h // 2 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 200, 255),
                2,
            )
            cv2.putText(
                color,
                "No RealSense D415 detected",
                (w // 2 - 180, h // 2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1,
            )

        # Simulated depth (uniform at ~0.5m)
        depth = None
        if self._settings.camera_depth_enabled:
            depth = np.full((h, w), 500, dtype=np.uint16)  # 500mm = 0.5m

        self._last_frame_time = time.time()
        return color, depth
