"use client";

import { Bell, BellOff, BellRing, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { enablePush, getPushPermission, isPushSupported } from "@/lib/web/push";

type Permission = NotificationPermission | "unsupported";

const rowClass =
  "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors";

export default function NotificationToggle() {
  const [permission, setPermission] = useState<Permission>("unsupported");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Notification.permission isn't readable during SSR, so resolve it on mount.
  useEffect(() => {
    setPermission(getPushPermission());
  }, []);

  if (!isPushSupported()) return null;

  async function handleEnable() {
    setBusy(true);
    setError(null);
    try {
      setPermission(await enablePush());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't enable notifications.");
    } finally {
      setBusy(false);
    }
  }

  if (permission === "granted") {
    return (
      <div className={`${rowClass} text-muted-foreground`}>
        <BellRing className="h-4 w-4 text-primary" />
        Notifications on
      </div>
    );
  }

  if (permission === "denied") {
    return (
      <div className={`${rowClass} text-muted-foreground`}>
        <BellOff className="h-4 w-4" />
        <span>Blocked — enable in browser settings</span>
      </div>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleEnable}
        disabled={busy}
        className={`${rowClass} text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-60`}
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Bell className="h-4 w-4" />
        )}
        Enable notifications
      </button>
      {error && <p className="px-3 pb-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}
