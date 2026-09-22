// Authentication domain contract types.

// Pydantic: UserLogin
export interface UserLogin {
  username: string;
  password: string;
}

// Pydantic: Token
export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string; // always "bearer" in practice
  expires_in: number; // seconds; backend default is 1800, always present
}

// Pydantic: RefreshTokenRequest
export interface RefreshTokenRequest {
  refresh_token: string;
}
