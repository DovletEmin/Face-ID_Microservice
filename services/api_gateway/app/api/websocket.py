"""API Gateway WebSocket proxy — streams camera feed to frontend."""

import asyncio
import logging

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()


@router.websocket("/ws/camera/stream")
async def proxy_camera_stream(websocket: WebSocket):
    """WebSocket proxy to camera service stream.

    Passes frames from camera-service to the frontend client.
    """
    await websocket.accept()

    # Build camera service WebSocket URL
    camera_ws_url = (
        f"ws://{settings.camera_service_host}:"
        f"{settings.camera_service_port}/ws/camera/stream"
    )

    try:
        async with websockets.connect(camera_ws_url) as camera_ws:
            # Forward frames from camera to client
            async def forward_to_client():
                async for message in camera_ws:
                    await websocket.send_text(message)

            # Forward control messages from client to camera
            async def forward_to_camera():
                while True:
                    try:
                        data = await websocket.receive_text()
                        await camera_ws.send(data)
                    except WebSocketDisconnect:
                        break

            forward_task = asyncio.create_task(forward_to_client())
            control_task = asyncio.create_task(forward_to_camera())

            done, pending = await asyncio.wait(
                [forward_task, control_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

    except websockets.exceptions.ConnectionClosed:
        logger.info("Camera WebSocket connection closed.")
    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
