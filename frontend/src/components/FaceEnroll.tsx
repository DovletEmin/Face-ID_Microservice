/** FaceEnroll — Face enrollment screen for new users. */

import { useState, useEffect, useCallback } from 'react';
import { CameraView } from './CameraView';
import { useCameraStream } from '../hooks/useCameraStream';
import { useAuthStore } from '../store/authStore';

interface FaceEnrollProps {
  onSwitchToLogin: () => void;
}

export function FaceEnroll({ onSwitchToLogin }: FaceEnrollProps) {
  const { isConnected, lastFrame, connect, disconnect } = useCameraStream();
  const { enrollFace, isLoading, error, clearError } = useAuthStore();

  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [step, setStep] = useState<'form' | 'capture' | 'done'>('form');

  useEffect(() => {
    if (step === 'capture') {
      connect();
    }
    return () => disconnect();
  }, [step, connect, disconnect]);

  const handleStartCapture = useCallback(() => {
    if (!username.trim()) return;
    clearError();
    setResult(null);
    setStep('capture');
  }, [username, clearError]);

  const handleCapture = useCallback(async () => {
    setScanning(true);

    // Trigger server-side camera capture and enrollment
    try {
      const enrollResult = await enrollFace(
        username.trim(),
        fullName.trim() || undefined,
      );

      setResult(enrollResult);
      if (enrollResult.success) {
        setStep('done');
      }
    } catch {
      setResult({ success: false, message: 'Enrollment failed.' });
    }

    setTimeout(() => setScanning(false), 1000);
  }, [username, fullName, enrollFace]);

  if (step === 'done') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md card text-center space-y-6">
          <div className="w-20 h-20 mx-auto bg-green-600/20 rounded-full flex items-center justify-center">
            <svg
              className="w-10 h-10 text-green-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-bold">Face Enrolled!</h2>
          <p className="text-gray-400">{result?.message}</p>
          <button onClick={onSwitchToLogin} className="btn-primary w-full">
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  if (step === 'capture') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold">Enrolling: {username}</h2>
            <p className="text-gray-400 mt-1">
              Look directly at the camera
            </p>
          </div>

          <div className="card">
            <CameraView
              frame={lastFrame}
              isConnected={isConnected}
              scanning={scanning}
              showDepth
            />

            {error && (
              <div className="mt-3 text-center text-sm text-red-400 bg-red-400/10 rounded-lg p-2">
                {error}
              </div>
            )}

            {result && !result.success && (
              <div className="mt-3 text-center text-sm text-yellow-400 bg-yellow-400/10 rounded-lg p-2">
                {result.message}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <button
              onClick={handleCapture}
              disabled={!isConnected || isLoading}
              className="btn-primary w-full"
            >
              {isLoading ? 'Capturing...' : 'Capture Face'}
            </button>
            <button
              onClick={() => { disconnect(); setStep('form'); }}
              className="btn-secondary w-full"
            >
              Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Form step
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">Register Face</h1>
          <p className="text-gray-400">Create your 3D face profile</p>
        </div>

        <div className="card space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Username *
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl
                         text-white placeholder-gray-500 focus:outline-none focus:border-blue-500
                         transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Full Name (optional)
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Enter full name"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl
                         text-white placeholder-gray-500 focus:outline-none focus:border-blue-500
                         transition-colors"
            />
          </div>

          <div className="pt-2 space-y-3">
            <button
              onClick={handleStartCapture}
              disabled={!username.trim()}
              className="btn-primary w-full"
            >
              Start Camera & Capture
            </button>
            <button onClick={onSwitchToLogin} className="btn-secondary w-full">
              Back to Login
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
