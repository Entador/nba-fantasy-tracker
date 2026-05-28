import { API_URL } from './config';
import { fetchAPI, refreshSession } from './client';
import type { AuthUser } from './types';

export async function register(
  email: string,
  password: string,
  rememberMe = true
): Promise<AuthUser> {
  return fetchAPI<AuthUser>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, remember_me: rememberMe }),
  });
}

/**
 * Log in. On success the backend sets the access_token + refresh_token cookies.
 * rememberMe=false makes the refresh cookie a session cookie (cleared on browser
 * close), so the user isn't kept signed in on a shared device.
 */
export async function login(
  email: string,
  password: string,
  rememberMe = false
): Promise<void> {
  // /token expects form-encoded data (OAuth2PasswordRequestForm), not JSON, and
  // names the email field "username". This header overrides fetchAPI's JSON default.
  const body = new URLSearchParams({
    username: email,
    password,
    remember_me: String(rememberMe),
  });
  await fetchAPI<unknown>('/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
}

export async function logout(): Promise<void> {
  await fetchAPI<void>('/auth/logout', { method: 'POST' });
}

/** Current user, or null for guests (a 401 is the normal "not signed in" case). */
export async function getCurrentUser(): Promise<AuthUser | null> {
  let res = await fetch(`${API_URL}/users/me`, { credentials: 'include' });
  // Access token may have expired while a valid refresh session remains (e.g. the
  // user returns the next day) — try one refresh before falling back to "guest".
  if (res.status === 401 && (await refreshSession())) {
    res = await fetch(`${API_URL}/users/me`, { credentials: 'include' });
  }
  if (!res.ok) return null;
  return res.json();
}
