import Cookies from "js-cookie";

const TOKEN_KEY = "insightx_token";
const USER_KEY = "insightx_user";

export interface StoredUser {
  user_id: string;
  username: string;
  email: string;
}

export function saveSession(token: string, user: StoredUser): void {
  Cookies.set(TOKEN_KEY, token, { expires: 1, sameSite: "strict" }); // 1 day
  if (typeof window !== "undefined") {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

export function getToken(): string | undefined {
  return Cookies.get(TOKEN_KEY);
}

export function getUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  Cookies.remove(TOKEN_KEY);
  if (typeof window !== "undefined") {
    localStorage.removeItem(USER_KEY);
  }
}

export function isLoggedIn(): boolean {
  return Boolean(getToken());
}
