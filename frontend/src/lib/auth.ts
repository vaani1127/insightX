import Cookies from "js-cookie";

const TOKEN_KEY = "insightx_token";

export interface StoredUser {
  user_id: string;
  username: string;
  email: string;
}

function decodeJwt(token: string): StoredUser | null {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    if (!decoded.sub || !decoded.email || !decoded.username) return null;
    return { user_id: decoded.sub, email: decoded.email, username: decoded.username };
  } catch {
    return null;
  }
}

export function saveSession(token: string): void {
  Cookies.set(TOKEN_KEY, token, { expires: 1, sameSite: "strict" });
}

export function getToken(): string | undefined {
  return Cookies.get(TOKEN_KEY);
}

export function getUser(): StoredUser | null {
  const token = getToken();
  if (!token) return null;
  return decodeJwt(token);
}

export function clearSession(): void {
  Cookies.remove(TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return Boolean(getToken());
}
