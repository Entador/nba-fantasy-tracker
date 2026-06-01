import { fetchAPI } from './client';
import type { Device, DevicePlatform } from './types';

/**
 * Register (or refresh) a push device for the signed-in user. Auth-only and
 * idempotent: re-posting the same token reactivates a revoked row and transfers
 * ownership if it belonged to another account. The browser-specific work of
 * producing a web `pushToken` lives in lib/web/push.ts.
 */
export async function registerDevice(
  pushToken: string,
  platform: DevicePlatform
): Promise<Device> {
  return fetchAPI<Device>('/api/devices/register', {
    method: 'POST',
    body: JSON.stringify({ push_token: pushToken, platform }),
  });
}

export async function unregisterDevice(id: number): Promise<void> {
  await fetchAPI<void>(`/api/devices/${id}`, { method: 'DELETE' });
}
