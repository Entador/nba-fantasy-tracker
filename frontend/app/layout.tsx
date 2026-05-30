import { BarChart2, Calendar, History, Trophy } from "lucide-react";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";

import AuthNav from "@/components/AuthNav";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "NBA Fantasy Tracker",
  description:
    "Track your Fantasy player picks and optimize your daily selections",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.className} min-h-screen bg-background antialiased flex flex-col`}
      >
        <nav className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur-md shadow-sm">
          <div className="container mx-auto px-3 sm:px-6 lg:px-8">
            <div className="flex h-14 sm:h-16 items-center justify-between">
              <Link
                href="/"
                aria-label="NBA Fantasy Tracker — home"
                className="flex items-center gap-2 text-base sm:text-xl font-bold tracking-tight hover:text-primary transition-colors"
              >
                <Trophy className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
                <p>NBA Fantasy Tracker</p>
              </Link>
              <div className="flex items-center text-sm sm:text-base gap-1 sm:gap-6">
                <Link
                  href="/"
                  aria-label="Dashboard"
                  className="flex items-center gap-1 px-2 sm:gap-1.5 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                >
                  <Calendar className="h-5 w-5" />
                  <span className="hidden sm:inline">Dashboard</span>
                </Link>
                <Link
                  href="/players"
                  aria-label="Rankings"
                  className="hidden sm:flex items-center gap-1 sm:gap-1.5 px-1 sm:px-2 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                >
                  <BarChart2 className="h-5 w-5" />
                  <span>Rankings</span>
                </Link>
                <Link
                  href="/history"
                  aria-label="History"
                  className="flex items-center gap-1 px-2 sm:gap-1.5 py-2 font-medium rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                >
                  <History className="h-5 w-5" />
                  <span className="hidden sm:inline">History</span>
                </Link>
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
              NBA Fantasy Tracker - Make smarter picks with data-driven insights
            </p>
            <p className="text-xs text-muted-foreground/70 mt-2">
              Elevate your fantasy basketball game
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
