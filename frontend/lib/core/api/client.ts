import { API_URL } from './config';

// MOBILE NOTE: credentials:'include' is the single web-specific assumption left
// in core. React Native should swap this file for a bearer-token variant.

/**
 * Try to renew the access token via the refresh cookie. Returns true on success.
 *
 * Deduped: concurrent 401s (snapshot + picks + /users/me all firing at once)
 * must NOT each call /auth/refresh — the token rotates on every call, so the
 * second would present an already-rotated token and fail. We share one in-flight
 * promise so they all await the same single refresh.
 */
let refreshInFlight: Promise<boolean> | null = null;

export function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then((res) => res.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

/**
 * On a 401 (expired access token) it transparently refreshes once and retries,
 * so a short-lived access token never surfaces as an error to the caller.
 */
export async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit,
  retry = true
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // send/receive the anon_id and auth cookies
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (response.status === 401 && retry && !endpoint.startsWith('/auth/')) {
      if (await refreshSession()) return fetchAPI<T>(endpoint, options, false);
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // 204 No Content (e.g. DELETE) has no body to parse.
    if (response.status === 204) return undefined as T;
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
