import useSWR, { useSWRConfig } from 'swr';

import {
  AuthUser,
  getCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from '@/lib/api';

const ME_KEY = '/users/me';
const PICKS_KEY = '/api/picks';

/**
 * Auth state, backed by the HttpOnly access_token cookie. We can't read the
 * cookie from JS, so we learn who the user is by calling GET /users/me (null for
 * guests). SWR shares this one cache key across the app, so any component calling
 * useAuth() sees the same user without a Context provider.
 *
 * Signing in/out changes the user's picks server-side (guest picks migrate to the
 * account on login), so we revalidate the picks cache after every auth change.
 */
export function useAuth() {
  const { mutate: globalMutate } = useSWRConfig();
  const { data: user, isLoading, mutate } = useSWR<AuthUser | null>(ME_KEY, getCurrentUser, {
    revalidateOnFocus: false,
    shouldRetryOnError: false, // a 401 means "guest", not a transient failure
  });

  async function refreshSession() {
    await Promise.all([mutate(), globalMutate(PICKS_KEY)]);
  }

  async function login(email: string, password: string) {
    await apiLogin(email, password);
    await refreshSession();
  }

  async function register(email: string, password: string) {
    await apiRegister(email, password);
    await refreshSession();
  }

  async function logout() {
    await apiLogout();
    await mutate(null, { revalidate: false }); // clear the user immediately
    await globalMutate(PICKS_KEY); // back to guest picks
  }

  return {
    user: user ?? null,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
  };
}
