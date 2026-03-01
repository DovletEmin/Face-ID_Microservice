/** Shared TypeScript types for the Face ID frontend. */

export interface User {
  id: string;
  username: string;
  full_name?: string;
  created_at?: string;
  enrollment_count?: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  username: string;
}

export interface AntiSpoofResult {
  is_real: boolean;
  confidence: number;
  depth_verified: boolean;
  method: string;
}

export interface AuthResponse {
  authenticated: boolean;
  user_id?: string;
  username?: string;
  confidence?: number;
  anti_spoof?: AntiSpoofResult;
  message: string;
}

export interface CameraInfo {
  status: 'connected' | 'disconnected' | 'error' | 'initializing';
  serial_number?: string;
  firmware_version?: string;
  frame_width: number;
  frame_height: number;
  fps: number;
  depth_enabled: boolean;
}

export interface FrameMessage {
  type: 'frame';
  frame_id: number;
  timestamp: number;
  color: string; // base64 JPEG
  depth_color?: string; // base64 JPEG (colorized depth)
}

export interface CapturedFrame {
  timestamp: number;
  color: string; // base64
  depth?: string; // base64 raw depth
  depth_shape?: number[];
  color_shape?: number[];
}

export interface EnrollResult {
  success: boolean;
  user_id?: string;
  message: string;
  quality_score: number;
}

export type AppView = 'login' | 'enroll' | 'dashboard';
