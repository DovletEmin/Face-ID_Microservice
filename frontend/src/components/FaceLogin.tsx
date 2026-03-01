/** FaceLogin — Face ID authentication screen. */

import { useState, useCallback, useEffect } from 'react';
import { CameraView } from './CameraView';
import { useCameraStream } from '../hooks/useCameraStream';
import { useAuthStore } from '../store/authStore';
import { api } from '../services/api';

interface FaceLoginProps {
  onSwitchToEnroll: () => void;
}

export function FaceLogin({ onSwitchToEnroll }: FaceLoginProps) {
  const { isConnected, lastFrame, connect, disconnect } = useCameraStream();
  const { loginWithFace, isLoading, error, clearError } = useAuthStore();
  const [scanning, setScanning] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  const handleLogin = useCallback(async () => {
    setScanning(true);
    setStatusMessage('Scanning face...');
    clearError();

    try {
      const success = await loginWithFace();
      if (success) {
        setStatusMessage('Authenticated!');
      } else {
        setStatusMessage('Recognition failed. Try again.');
      }
    } catch {
      setStatusMessage('Error during authentication.');
    }

    // Keep scanning animation for a moment
    setTimeout(() => setScanning(false), 1500);
  }, [loginWithFace, clearError]);

  // Auto-scan when camera is connected
  const handleAutoScan = useCallback(async () => {
    if (!isConnected || isLoading) return;

    // Use server-side capture for authentication
    handleLogin();
  }, [isConnected, isLoading, handleLogin]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-20 h-20 mx-auto bg-blue-600/20 rounded-full flex items-center justify-center mb-4">
            <svg
              className="w-10 h-10 text-blue-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white">Face ID</h1>
          <p className="text-gray-400">3D Face Recognition System</p>
        </div>

        {/* Camera feed */}
        <div className="card">
          <CameraView
            frame={lastFrame}
            isConnected={isConnected}
            scanning={scanning}
          />

          {/* Status message */}
          {statusMessage && (
            <div className="mt-3 text-center text-sm text-gray-400">
              {statusMessage}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-3 text-center text-sm text-red-400 bg-red-400/10 rounded-lg p-2">
              {error}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={handleAutoScan}
            disabled={!isConnected || isLoading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <svg
                  className="w-5 h-5 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Scanning...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
                Scan Face to Login
              </>
            )}
          </button>

          <button
            onClick={onSwitchToEnroll}
            className="btn-secondary w-full"
          >
            Register New Face
          </button>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-600">
          Powered by Intel RealSense D415 + ArcFace
        </p>
      </div>
    </div>
  );
}
