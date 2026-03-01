/** Hook for WebSocket camera streaming. */

import { useEffect, useRef, useState, useCallback } from 'react';
import { CameraWebSocket } from '../services/websocket';
import type { FrameMessage } from '../types';

interface UseCameraStreamResult {
  isConnected: boolean;
  lastFrame: FrameMessage | null;
  connect: () => void;
  disconnect: () => void;
  pause: () => void;
  resume: () => void;
}

export function useCameraStream(): UseCameraStreamResult {
  const [isConnected, setIsConnected] = useState(false);
  const [lastFrame, setLastFrame] = useState<FrameMessage | null>(null);
  const wsRef = useRef<CameraWebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/camera/stream`;

    wsRef.current = new CameraWebSocket(
      url,
      (frame) => setLastFrame(frame),
      (connected) => setIsConnected(connected),
    );
    wsRef.current.connect();
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
    wsRef.current = null;
    setIsConnected(false);
    setLastFrame(null);
  }, []);

  const pause = useCallback(() => wsRef.current?.pause(), []);
  const resume = useCallback(() => wsRef.current?.resume(), []);

  useEffect(() => {
    return () => {
      wsRef.current?.disconnect();
    };
  }, []);

  return { isConnected, lastFrame, connect, disconnect, pause, resume };
}
