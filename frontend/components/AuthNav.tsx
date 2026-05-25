"use client";

import { LogIn, LogOut } from "lucide-react";
import Link from "next/link";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useAuth } from "@/lib/hooks/useAuth";

const navItemClass =
  "flex items-center gap-1 px-1 sm:px-2 sm:gap-1.5 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all";

export default function AuthNav() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  // Hold the space while we resolve the session, so the nav doesn't jump.
  if (isLoading) {
    return <div className="h-9 w-9" aria-hidden />;
  }

  if (!isAuthenticated) {
    return (
      <Link href="/login" className={navItemClass}>
        <LogIn className="h-5 w-5" />
        <span className="hidden sm:inline">Sign in</span>
      </Link>
    );
  }

  const initial = user?.email?.[0]?.toUpperCase() ?? "?";

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Account menu"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold shadow-sm transition-all hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          {initial}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-0">
        <div className="flex items-center gap-3 border-b p-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
            {initial}
          </div>
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">Signed in as</p>
            <p className="truncate text-sm font-medium" title={user?.email ?? undefined}>
              {user?.email}
            </p>
          </div>
        </div>
        <div className="p-2">
          <button
            type="button"
            onClick={() => logout()}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
