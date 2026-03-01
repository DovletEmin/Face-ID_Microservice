/** CameraView — displays live camera feed with face detection overlay. */

import { useEffect, useRef } from 'react';
import type { FrameMessage } from '../types';

interface CameraViewProps {
  frame: FrameMessage | null;
  isConnected: boolean;
  showDepth?: boolean;
  scanning?: boolean;
  className?: string;
}

export function CameraView({
  frame,
  isConnected,
  showDepth = false,
  scanning = false,
  className = '',
}: CameraViewProps) {
  const colorRef = useRef<HTMLImageElement>(null);
  const depthRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (!frame) return;

    if (colorRef.current && frame.color) {
      colorRef.current.src = `data:image/jpeg;base64,${frame.color}`;
    }
    if (depthRef.current && frame.depth_color) {
      depthRef.current.src = `data:image/jpeg;base64,${frame.depth_color}`;
    }
  }, [frame]);

  return (
    <div className={`relative overflow-hidden rounded-2xl bg-gray-900 ${className}`}>
      {/* Color feed */}
      <div className="relative aspect-[4/3] w-full">
        {isConnected && frame ? (
          <img
            ref={colorRef}
            alt="Camera feed"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-gray-700 flex items-center justify-center">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <p className="text-sm">
                {isConnected ? 'Waiting for frames...' : 'Camera disconnected'}
              </p>
            </div>
          </div>
        )}

        {/* Face scan overlay */}
        {scanning && (
          <div className="face-scan-overlay">
            <div className="face-scan-ring">
              <div className="scan-line" />
            </div>
          </div>
        )}

        {/* Connection indicator */}
        <div className="absolute top-3 right-3 flex items-center gap-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isConnected ? 'bg-green-400 shadow-green-400/50' : 'bg-red-400'
            } shadow-lg`}
          />
          <span className="text-xs text-white/70 bg-black/40 px-2 py-0.5 rounded-full">
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        {/* Frame counter */}
        {frame && (
          <div className="absolute bottom-3 left-3 text-xs text-white/50 bg-black/40 px-2 py-0.5 rounded">
            Frame #{frame.frame_id}
          </div>
        )}
      </div>

      {/* Depth view (optional) */}
      {showDepth && frame?.depth_color && (
        <div className="mt-2 aspect-[4/3] w-full relative rounded-xl overflow-hidden">
          <img
            ref={depthRef}
            alt="Depth view"
            className="w-full h-full object-cover"
          />
          <div className="absolute top-2 left-2 text-xs text-white/70 bg-black/40 px-2 py-0.5 rounded">
            DEPTH MAP
          </div>
        </div>
      )}
    </div>
  );
}
