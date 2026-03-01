/** API client for backend communication. */

const API_BASE = '/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      h['Authorization'] = `Bearer ${this.token}`;
    }
    return h;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const resp = await fetch(`${API_BASE}${path}`, {
      method,
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!resp.ok) {
      const error = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(error.detail || `HTTP ${resp.status}`);
    }

    return resp.json();
  }

  // Auth
  async loginFace() {
    return this.request<{
      access_token: string;
      token_type: string;
      expires_in: number;
      user_id: string;
      username: string;
    }>('POST', '/auth/login/face');
  }

  async loginFaceWithFrame(data: {
    color_frame_b64: string;
    depth_data_b64?: string;
    depth_shape?: number[];
  }) {
    return this.request<{
      access_token: string;
      token_type: string;
      expires_in: number;
      user_id: string;
      username: string;
    }>('POST', '/auth/login/face/frame', data);
  }

  async enrollFace(data: { username: string; full_name?: string }) {
    return this.request<{
      success: boolean;
      user_id?: string;
      message: string;
      quality_score: number;
    }>('POST', '/auth/enroll', data);
  }

  async enrollFaceWithFrame(data: {
    username: string;
    full_name?: string;
    color_frame_b64: string;
    depth_data_b64?: string;
    depth_shape?: number[];
  }) {
    return this.request<{
      success: boolean;
      user_id?: string;
      message: string;
      quality_score: number;
    }>('POST', '/auth/enroll/frame', data);
  }

  async verifyToken() {
    return this.request<{
      valid: boolean;
      user_id?: string;
      username?: string;
      message: string;
    }>('POST', '/auth/verify');
  }

  async logout() {
    return this.request<{ message: string }>('POST', '/auth/logout');
  }

  // Camera
  async getCameraInfo() {
    return this.request<{
      status: string;
      serial_number?: string;
      firmware_version?: string;
      frame_width: number;
      frame_height: number;
      fps: number;
      depth_enabled: boolean;
    }>('GET', '/camera/info');
  }

  async captureFrame() {
    return this.request<{
      timestamp: number;
      color: string;
      depth?: string;
      depth_shape?: number[];
      color_shape?: number[];
    }>('POST', '/camera/capture');
  }

  // Face
  async listUsers() {
    return this.request<
      Array<{
        id: string;
        username: string;
        full_name?: string;
        created_at?: string;
        enrollment_count: number;
      }>
    >('GET', '/face/users');
  }

  // Health
  async health() {
    return this.request<{
      status: string;
      service: string;
      services: Record<string, string>;
    }>('GET', '/health');
  }
}

export const api = new ApiClient();
