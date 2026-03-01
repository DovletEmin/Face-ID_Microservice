/** WebSocket client for real-time camera streaming. */

import type { FrameMessage } from '../types';

export type FrameCallback = (frame: FrameMessage) => void;

export class CameraWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onFrame: FrameCallback;
  private onStatusChange: (connected: boolean) => void;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;

  constructor(
    url: string,
    onFrame: FrameCallback,
    onStatusChange: (connected: boolean) => void,
  ) {
    this.url = url;
    this.onFrame = onFrame;
    this.onStatusChange = onStatusChange;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        console.log('[WS] Connected to camera stream');
        this.onStatusChange(true);
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data: FrameMessage = JSON.parse(event.data);
          if (data.type === 'frame') {
            this.onFrame(data);
          }
        } catch {
          // Ignore parse errors
        }
      };

      this.ws.onclose = () => {
        console.log('[WS] Disconnected');
        this.onStatusChange(false);
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.onStatusChange(false);
      };
    } catch (e) {
      console.error('[WS] Connection error:', e);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  pause(): void {
    this.send({ action: 'pause' });
  }

  resume(): void {
    this.send({ action: 'resume' });
  }

  private send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect) return;
    if (this.reconnectTimer) return;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      console.log('[WS] Reconnecting...');
      this.connect();
    }, 2000);
  }
}
