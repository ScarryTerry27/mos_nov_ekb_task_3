export interface LoginRequest {
  name: string;
  password: string;
}

export interface LoginResponse {
  name: string;
  role: string;
  user_id: number;
}