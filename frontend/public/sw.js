// Service worker for web push. Kept dependency-free and tiny — it only needs to
// render incoming pushes and route a click back into the app.
//
// Payload shape (see backend notifications/notifier.py WebPushNotifier.send):
//   { title, body, data: { url?, ... } }

self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    // Non-JSON payload (shouldn't happen) — fall back to raw text as the body.
    payload = { body: event.data ? event.data.text() : '' };
  }

  const title = payload.title || 'NBA Fantasy Tracker';
  const options = {
    body: payload.body || '',
    data: payload.data || {},
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/';

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus an existing tab if the app is already open, else open one.
        const existing = clientList.find((c) => 'focus' in c);
        if (existing) {
          existing.navigate?.(targetUrl);
          return existing.focus();
        }
        return self.clients.openWindow(targetUrl);
      })
  );
});
