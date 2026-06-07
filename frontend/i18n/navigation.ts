import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

// Locale-aware wrappers around Next.js navigation APIs. Use these (not the ones
// from `next/navigation` / `next/link`) for internal navigation so the active
// locale prefix is preserved.
export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
