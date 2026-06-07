import { BarChart2, Calendar, History, Trophy } from "lucide-react";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import AuthNav from "@/components/AuthNav";
import ThemeToggle from "@/components/ThemeToggle";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import "../globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Metadata" });
  return {
    title: t("title"),
    description: t("description"),
  };
}

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);

  const t = await getTranslations("Nav");

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');var d=t==='dark'||(t===null&&window.matchMedia('(prefers-color-scheme: dark)').matches);var e=document.documentElement;if(d){e.classList.add('dark')}e.style.colorScheme=d?'dark':'light'})()`,
          }}
        />
      </head>
      <body
        className={`${inter.className} min-h-screen bg-background antialiased flex flex-col`}
      >
        <NextIntlClientProvider>
          <nav className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur-md shadow-sm">
            <div className="container mx-auto px-3 sm:px-6 lg:px-8">
              <div className="flex h-14 sm:h-16 items-center justify-between">
                <Link
                  href="/"
                  aria-label={t("home")}
                  className="flex items-center gap-2 text-base sm:text-xl font-bold tracking-tight hover:text-primary transition-colors"
                >
                  <Trophy className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
                  <p>{t("brand")}</p>
                </Link>
                <div className="flex items-center text-sm sm:text-base gap-1 sm:gap-6">
                  <Link
                    href="/"
                    aria-label={t("dashboard")}
                    className="flex items-center gap-1 px-2 sm:gap-1.5 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                  >
                    <Calendar className="h-5 w-5" />
                    <span className="hidden sm:inline">{t("dashboard")}</span>
                  </Link>
                  <Link
                    href="/players"
                    aria-label={t("rankings")}
                    className="hidden sm:flex items-center gap-1 sm:gap-1.5 px-1 sm:px-2 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                  >
                    <BarChart2 className="h-5 w-5" />
                    <span>{t("rankings")}</span>
                  </Link>
                  <Link
                    href="/history"
                    aria-label={t("history")}
                    className="flex items-center gap-1 px-2 sm:gap-1.5 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                  >
                    <History className="h-5 w-5" />
                    <span className="hidden sm:inline">{t("history")}</span>
                  </Link>
                  <ThemeToggle />
                  <AuthNav />
                </div>
              </div>
            </div>
          </nav>
          <main className="flex-1 container mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-8">
            {children}
          </main>
          <footer className="border-t bg-muted/30">
            <div className="container mx-auto px-4 py-5 text-center">
              <p className="text-sm text-muted-foreground">
                {t("footerTagline")}
              </p>
              <p className="text-xs text-muted-foreground/70 mt-2">
                {t("footerSubtitle")}
              </p>
            </div>
          </footer>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
