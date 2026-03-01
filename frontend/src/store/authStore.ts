/** Authentication state management using Zustand. */

import { create } from 'zustand';
import { api } from '../services/api';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  userId: string | null;
  username: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  loginWithFace: () => Promise<boolean>;
  loginWithFrame: (
    colorB64: string,
    depthB64?: string,
    depthShape?: number[],
  ) => Promise<boolean>;
  enrollWithFrame: (
    username: string,
    fullName: string | undefined,
    colorB64: string,
    depthB64?: string,
    depthShape?: number[],
  ) => Promise<{ success: boolean; message: string }>;
  enrollFace: (
    username: string,
    fullName?: string,
  ) => Promise<{ success: boolean; message: string }>;
  logout: () => void;
  restoreSession: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  token: null,
  userId: null,
  username: null,
  isLoading: false,
  error: null,

  loginWithFace: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.loginFace();
      api.setToken(result.access_token);
      localStorage.setItem('face_id_token', result.access_token);

      set({
        isAuthenticated: true,
        token: result.access_token,
        userId: result.user_id,
        username: result.username,
        isLoading: false,
      });
      return true;
    } catch (e) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'Authentication failed',
      });
      return false;
    }
  },

  loginWithFrame: async (colorB64, depthB64, depthShape) => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.loginFaceWithFrame({
        color_frame_b64: colorB64,
        depth_data_b64: depthB64,
        depth_shape: depthShape,
      });
      api.setToken(result.access_token);
      localStorage.setItem('face_id_token', result.access_token);

      set({
        isAuthenticated: true,
        token: result.access_token,
        userId: result.user_id,
        username: result.username,
        isLoading: false,
      });
      return true;
    } catch (e) {
      set({
        isLoading: false,
        error: e instanceof Error ? e.message : 'Authentication failed',
      });
      return false;
    }
  },

  enrollWithFrame: async (username, fullName, colorB64, depthB64, depthShape) => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.enrollFaceWithFrame({
        username,
        full_name: fullName,
        color_frame_b64: colorB64,
        depth_data_b64: depthB64,
        depth_shape: depthShape,
      });
      set({ isLoading: false });
      return { success: result.success, message: result.message };
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Enrollment failed';
      set({ isLoading: false, error: msg });
      return { success: false, message: msg };
    }
  },

  enrollFace: async (username, fullName) => {
    set({ isLoading: true, error: null });
    try {
      const result = await api.enrollFace({ username, full_name: fullName });
      set({ isLoading: false });
      return { success: result.success, message: result.message };
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Enrollment failed';
      set({ isLoading: false, error: msg });
      return { success: false, message: msg };
    }
  },

  logout: () => {
    api.setToken(null);
    localStorage.removeItem('face_id_token');
    set({
      isAuthenticated: false,
      token: null,
      userId: null,
      username: null,
      error: null,
    });
  },

  restoreSession: async () => {
    const token = localStorage.getItem('face_id_token');
    if (!token) return;

    api.setToken(token);
    try {
      const result = await api.verifyToken();
      if (result.valid) {
        set({
          isAuthenticated: true,
          token,
          userId: result.user_id ?? null,
          username: result.username ?? null,
        });
      } else {
        localStorage.removeItem('face_id_token');
        api.setToken(null);
      }
    } catch {
      localStorage.removeItem('face_id_token');
      api.setToken(null);
    }
  },

  clearError: () => set({ error: null }),
}));
