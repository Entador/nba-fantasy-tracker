import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  // French is the primary audience; English is the alternate.
  locales: ["fr", "en"],
  defaultLocale: "fr",
  // Keep default-locale (French) URLs clean: "/" for fr, "/en" for en.
  localePrefix: "as-needed",
});

export type Locale = (typeof routing.locales)[number];
