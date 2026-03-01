"""Frame streaming manager.

Manages real-time streaming of color and depth frames
via WebSocket connections, with frame rate control.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Optional, Set

import cv2
import numpy as np

from app.camera.realsense import RealSenseCamera
from app.camera.depth import DepthProcessor
from app.config import get_settings

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages camera frame streaming to WebSocket clients."""

    def __init__(
        self, camera: RealSenseCamera, depth_processor: DepthProcessor
    ) -> None:
        self._camera = camera
        self._depth = depth_processor
        self._settings = get_settings()
        self._clients: Set[asyncio.Queue] = set()
        self._is_streaming: bool = False
        self._frame_count: int = 0
        self._stream_task: Optional[asyncio.Task] = None

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    async def add_client(self) -> asyncio.Queue:
        """Register a new streaming client.

        Returns:
            Queue for receiving encoded frames.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=5)
        self._clients.add(queue)
        logger.info(f"Client connected. Total clients: {len(self._clients)}")

        if not self._is_streaming:
            await self.start_streaming()

        return queue

    async def remove_client(self, queue: asyncio.Queue) -> None:
        """Unregister a streaming client."""
        self._clients.discard(queue)
        logger.info(f"Client disconnected. Total clients: {len(self._clients)}")

        if len(self._clients) == 0:
            await self.stop_streaming()

    async def start_streaming(self) -> None:
        """Start the frame capture and broadcast loop."""
        if self._is_streaming:
            return
        self._is_streaming = True
        self._stream_task = asyncio.create_task(self._stream_loop())
        logger.info("Streaming started.")

    async def stop_streaming(self) -> None:
        """Stop the streaming loop."""
        self._is_streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        logger.info("Streaming stopped.")

    async def capture_single_frame(self) -> Optional[dict]:
        """Capture a single frame with color + depth data.

        Used for face enrollment/authentication (not streaming).

        Returns:
            Dictionary with base64-encoded color frame and depth data.
        """
        color_frame, depth_frame = await asyncio.get_running_loop().run_in_executor(
            None, self._camera.get_frames
        )

        if color_frame is None:
            return None

        # Encode color frame
        _, color_jpg = cv2.imencode(
            ".jpg",
            color_frame,
            [cv2.IMWRITE_JPEG_QUALITY, 95],
        )
        color_b64 = base64.b64encode(color_jpg.tobytes()).decode("utf-8")

        result = {
            "timestamp": time.time(),
            "color": color_b64,
            "color_shape": list(color_frame.shape),
        }

        # Include raw depth data for face processing
        if depth_frame is not None:
            depth_b64 = base64.b64encode(depth_frame.tobytes()).decode("utf-8")
            result["depth"] = depth_b64
            result["depth_shape"] = list(depth_frame.shape)
            result["depth_dtype"] = str(depth_frame.dtype)

        return result

    async def _stream_loop(self) -> None:
        """Main streaming loop — captures frames and broadcasts to clients."""
        target_interval = 1.0 / self._settings.camera_fps

        while self._is_streaming:
            loop_start = time.monotonic()

            try:
                # Capture frame in thread pool to avoid blocking event loop
                color_frame, depth_frame = (
                    await asyncio.get_running_loop().run_in_executor(
                        None, self._camera.get_frames
                    )
                )

                if color_frame is None:
                    await asyncio.sleep(0.05)
                    continue

                # Encode color frame for streaming
                _, color_jpg = cv2.imencode(
                    ".jpg",
                    color_frame,
                    [cv2.IMWRITE_JPEG_QUALITY, self._settings.stream_jpeg_quality],
                )
                color_b64 = base64.b64encode(color_jpg.tobytes()).decode("utf-8")

                # Build frame message
                message = {
                    "type": "frame",
                    "frame_id": self._frame_count,
                    "timestamp": time.time(),
                    "color": color_b64,
                }

                # Add depth visualization if available
                if depth_frame is not None:
                    depth_colored = self._depth.colorize_depth(depth_frame)
                    _, depth_jpg = cv2.imencode(
                        ".jpg",
                        depth_colored,
                        [cv2.IMWRITE_JPEG_QUALITY, 70],
                    )
                    message["depth_color"] = base64.b64encode(
                        depth_jpg.tobytes()
                    ).decode("utf-8")

                # Broadcast to all clients
                frame_json = json.dumps(message)
                dead_clients = set()

                for client_queue in self._clients:
                    try:
                        if client_queue.full():
                            # Drop oldest frame to prevent lag
                            try:
                                client_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                        client_queue.put_nowait(frame_json)
                    except Exception:
                        dead_clients.add(client_queue)

                # Clean up dead clients
                self._clients -= dead_clients
                self._frame_count += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream loop error: {e}")
                await asyncio.sleep(0.1)

            # Frame rate control
            elapsed = time.monotonic() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
