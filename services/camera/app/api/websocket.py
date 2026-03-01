"""Camera service WebSocket endpoint for real-time frame streaming."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_stream_manager():
    from app.main import stream_manager

    return stream_manager


@router.websocket("/ws/camera/stream")
async def camera_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time camera frame streaming.

    Sends JSON messages with base64-encoded color and depth frames.
    Client can send control messages:
        - {"action": "pause"} - pause streaming
        - {"action": "resume"} - resume streaming
    """
    await websocket.accept()
    stream = _get_stream_manager()
    queue = await stream.add_client()
    paused = False

    logger.info(f"WebSocket client connected from {websocket.client}")

    try:
        # Create tasks for sending frames and receiving control messages
        async def send_frames():
            nonlocal paused
            while True:
                frame_json = await queue.get()
                if not paused:
                    await websocket.send_text(frame_json)

        async def receive_controls():
            nonlocal paused
            while True:
                try:
                    data = await websocket.receive_json()
                    action = data.get("action", "")
                    if action == "pause":
                        paused = True
                        logger.debug("Client paused streaming")
                    elif action == "resume":
                        paused = False
                        logger.debug("Client resumed streaming")
                except Exception:
                    break

        send_task = asyncio.create_task(send_frames())
        recv_task = asyncio.create_task(receive_controls())

        done, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await stream.remove_client(queue)
