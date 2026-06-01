// Browser-only web push wiring. Lives in lib/web (not core) because it touches
// ServiceWorker, PushManager and Notification — none of which exist in React
// Native. The mobile app registers an Expo token instead, reusing registerDevice.

import { registerDevice } from '@/lib/core/api';

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
const SW_URL = '/sw.js';

/** True when the browser can do service-worker push at all. */
export function isPushSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

/** Current Notification permission, or 'unsupported' when push isn't available. */
export function getPushPermission(): NotificationPermission | 'unsupported' {
  if (!isPushSupported()) return 'unsupported';
  return Notification.permission;
}

/**
 * Ask for permission, subscribe to push, and register the subscription as a
 * `web` device. Must be called from a user gesture (browsers reject permission
 * prompts otherwise). Returns the resulting permission so the UI can react.
 *
 * Idempotent: an existing subscription is reused, and registerDevice upserts by
 * token, so calling this repeatedly is safe.
 */
export async function enablePush(): Promise<NotificationPermission> {
  if (!isPushSupported()) {
    throw new Error('Push notifications are not supported in this browser.');
  }
  if (!VAPID_PUBLIC_KEY) {
    throw new Error('Missing NEXT_PUBLIC_VAPID_PUBLIC_KEY.');
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return permission;

  const registration = await navigator.serviceWorker.register(SW_URL);
  await navigator.serviceWorker.ready;

  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    }));

  // The backend stores the whole subscription JSON as the push token.
  await registerDevice(JSON.stringify(subscription), 'web');
  return permission;
}

// applicationServerKey wants a Uint8Array of the raw VAPID public key; the key
// ships as a URL-safe base64 string, so decode it here.
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(normalized);
  // Back the array with a concrete ArrayBuffer so the type satisfies BufferSource
  // (a bare `new Uint8Array(n)` infers ArrayBufferLike, which PushManager rejects).
  const output = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) output[i] = raw.charCodeAt(i);
  return output;
}
