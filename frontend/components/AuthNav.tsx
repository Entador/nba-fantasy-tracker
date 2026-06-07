"use client";

import { Globe, LogIn, LogOut, User } from "lucide-react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import NotificationToggle from "@/components/NotificationToggle";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useAuth } from "@/lib/core/hooks/useAuth";

const navItemClass =
  "flex items-center gap-1 px-1 sm:px-2 sm:gap-1.5 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all";

export default function AuthNav() {
  const t = useTranslations("Auth");
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  // Hold the space while we resolve the session, so the nav doesn't jump.
  if (isLoading) {
    return <div className="h-9 w-9" aria-hidden />;
  }

  if (!isAuthenticated) {
    return (
      <>
        <LocaleSwitcher />
        <Link href="/login" className={navItemClass}>
          <LogIn className="h-5 w-5" />
          <span className="hidden sm:inline">{t("signIn")}</span>
        </Link>
      </>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={t("accountMenu")}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm transition-all hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <User className="h-5 w-5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-0">
        <div className="flex items-center gap-3 border-b p-4">
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">{t("signedInAs")}</p>
            <p
              className="truncate text-sm font-medium"
              title={user?.email ?? undefined}
            >
              {user?.email}
            </p>
          </div>
        </div>
        <div className="p-2">
          <div className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground">
            <Globe className="h-4 w-4 shrink-0" />
            <span className="flex-1">{t("language")}</span>
            <LocaleSwitcher />
          </div>
          <NotificationToggle />
          <button
            type="button"
            onClick={() => logout()}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
            {t("signOut")}
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
