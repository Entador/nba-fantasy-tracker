"use client";

import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/web/cn";

/**
 * Compact FR / EN toggle. Switches the locale while staying on the current path
 * (preserving the dynamic route params), and persists the choice via the
 * next-intl cookie.
 */
export default function LocaleSwitcher() {
  const t = useTranslations("LocaleSwitcher");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  function switchTo(next: string) {
    if (next === locale) return;
    startTransition(() => {
      // `pathname` is locale-agnostic (already stripped of the prefix), so we
      // stay on the current route and just swap the locale.
      router.replace(pathname, { locale: next });
    });
  }

  return (
    <div
      className="flex items-center rounded-full border border-input text-xs font-medium"
      role="group"
      aria-label={t("label")}
    >
      {routing.locales.map((loc) => (
        <button
          key={loc}
          type="button"
          onClick={() => switchTo(loc)}
          disabled={isPending}
          aria-pressed={loc === locale}
          className={cn(
            "px-2 py-1 rounded-full transition-colors disabled:opacity-50",
            loc === locale
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {t(loc)}
        </button>
      ))}
    </div>
  );
}
