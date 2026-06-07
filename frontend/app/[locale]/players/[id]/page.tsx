"use client";

import { ScoreBadge } from "@/components/ScoreBadge";
import { ScoreChart } from "@/components/ScoreChart";
import { TeamLogo } from "@/components/TeamLogo";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getPlayerStats, type PlayerStats } from "@/lib/core/api";
import { usePicks } from "@/lib/core/hooks/usePicks";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Target,
  TrendingUp,
  Trophy,
} from "lucide-react";
import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const LOGO_SIZE = 40;

export default function PlayerDetailPage() {
  const t = useTranslations("PlayerDetail");
  const locale = useLocale();
  const params = useParams();
  const router = useRouter();
  const playerId = parseInt(params.id as string);
  const { picks } = usePicks();

  const [data, setData] = useState<PlayerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (playerId) {
      loadPlayerStats();
    }
  }, [playerId]);

  async function loadPlayerStats() {
    try {
      setLoading(true);
      setError(null);
      const stats = await getPlayerStats(playerId);
      setData(stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errorTitle"));
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 animate-fade-in">
        <div className="relative">
          <div className="w-20 h-20 rounded-full border-4 border-muted absolute"></div>
          <Loader2 className="h-20 w-20 animate-spin text-primary" />
        </div>
        <p className="text-lg font-semibold mt-8 text-foreground">
          {t("loading")}
        </p>
        <p className="text-sm text-muted-foreground mt-2 animate-pulse-subtle">
          {t("loadingSub")}
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-destructive/50 shadow-lg animate-slide-up">
        <CardContent className="flex flex-col items-center py-16">
          <div className="p-4 rounded-full bg-destructive/10 mb-6">
            <AlertCircle className="h-16 w-16 text-destructive" />
          </div>
          <h3 className="text-2xl font-bold mb-2">{t("errorTitle")}</h3>
          <p className="text-muted-foreground mb-6 text-center max-w-md">
            {error || t("notFound")}
          </p>
          <Button size="lg" className="shadow-md" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t("backToDashboard")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const pickedGames = picks.filter((p) => p.playerId === playerId);
  const pickedDates = new Set(pickedGames.map((p) => p.date));
  const playedGames = data.recent_games
    .filter((g) => !g.dnp)
    .map((g) => ({ ...g, picked: pickedDates.has(g.game_date) }));
  const gamesWhenPicked = playedGames.filter((g) => g.picked);
  const avgPicked =
    gamesWhenPicked.length > 0
      ? (
          gamesWhenPicked.reduce((sum, g) => sum + g.fantasy_score, 0) /
          gamesWhenPicked.length
        ).toFixed(1)
      : "0.0";

  const { best_score, worst_score, std_dev, consistency } = data;
  const consistencyLabel =
    consistency === "High"
      ? t("valueHigh")
      : consistency === "Medium"
        ? t("valueMedium")
        : t("valueLow");

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="animate-slide-up">
        <Button
          variant="ghost"
          className="mb-3 hover:bg-accent transition-all"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("backToDashboard")}
        </Button>
        <div className="flex items-center gap-3 sm:gap-4">
          <Image
            src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${data.player.id}.png`}
            alt={data.player.name}
            width={90}
            height={70}
            className="rounded-lg object-cover hidden sm:block"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
          <Image
            src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${data.player.id}.png`}
            alt={data.player.name}
            width={60}
            height={45}
            className="rounded-lg object-cover sm:hidden"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-black tracking-tight bg-linear-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
            {data.player.name}
          </h1>
          <span className="sm:hidden">
            <TeamLogo team={data.player.team} size={35} />
          </span>
          <span className="hidden sm:block">
            <TeamLogo team={data.player.team} size={60} />
          </span>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
        <Card className="border-l-4 border-l-primary hover:shadow-lg transition-all duration-300">
          <CardHeader className="pb-1 sm:pb-2 pt-3 sm:pt-4 px-3 sm:px-6">
            <CardDescription className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold">
              <div className="p-1 sm:p-1.5 rounded-lg bg-primary/10">
                <TrendingUp className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-primary" />
              </div>
              {t("avgFantasy")}
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-3 sm:pb-4 px-3 sm:px-6">
            <div className="text-2xl sm:text-3xl font-black bg-linear-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">
              {data.avg_fantasy.toFixed(1)}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5 sm:mt-1 font-medium">
              {t("lastGamesPlayed", { count: playedGames.length })}
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500 hover:shadow-lg transition-all duration-300">
          <CardHeader className="pb-1 sm:pb-2 pt-3 sm:pt-4 px-3 sm:px-6">
            <CardDescription className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold">
              <div className="p-1 sm:p-1.5 rounded-lg bg-green-500/10">
                <Target className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-green-600" />
              </div>
              {t("timesPicked")}
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-3 sm:pb-4 px-3 sm:px-6">
            <div className="text-2xl sm:text-3xl font-black bg-linear-to-br from-green-600 to-green-500 bg-clip-text text-transparent">
              {pickedGames.length}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5 sm:mt-1 font-medium">
              {pickedGames.length > 0
                ? t("avgPts", { avg: avgPicked })
                : t("notPicked")}
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500 hover:shadow-lg transition-all duration-300">
          <CardHeader className="pb-1 sm:pb-2 pt-3 sm:pt-4 px-3 sm:px-6">
            <CardDescription className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold">
              <div className="p-1 sm:p-1.5 rounded-lg bg-amber-500/10">
                <Trophy className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-amber-600" />
              </div>
              {t("bestPerformance")}
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-3 sm:pb-4 px-3 sm:px-6">
            <div className="text-2xl sm:text-3xl font-black">{best_score}</div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5 sm:mt-1 font-medium">
              {t("worst", { score: worst_score })}
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-blue-500 hover:shadow-lg transition-all duration-300">
          <CardHeader className="pb-1 sm:pb-2 pt-3 sm:pt-4 px-3 sm:px-6">
            <CardDescription className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold">
              <div className="p-1 sm:p-1.5 rounded-lg bg-blue-500/10">
                <CheckCircle2 className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-blue-600" />
              </div>
              {t("consistency")}
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-3 sm:pb-4 px-3 sm:px-6">
            <div className="text-2xl sm:text-3xl font-black bg-linear-to-br from-blue-600 to-blue-500 bg-clip-text text-transparent">
              {consistencyLabel}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5 sm:mt-1 font-medium">
              {t("stdDev", { value: std_dev.toFixed(1) })}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Games - Table + Chart + Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:items-start">
        {/* Left: Recent Games Table */}
        <Card className="lg:max-h-[600px] flex flex-col">
          <CardHeader className="pb-3 shrink-0">
            <CardTitle className="text-lg">{t("recentGames")}</CardTitle>
            <CardDescription className="text-sm">
              {t("recentGamesDesc", {
                total: data.recent_games.length,
                played: playedGames.length,
              })}
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-4 overflow-y-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="h-8 py-1">{t("date")}</TableHead>
                  <TableHead className="h-8 py-1">{t("matchup")}</TableHead>
                  <TableHead className="text-right h-8 py-1">
                    {t("fantasyScore")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.recent_games.map((game, index) => (
                  <TableRow
                    key={index}
                    className={pickedDates.has(game.game_date) ? "bg-muted/50" : ""}
                  >
                    <TableCell className="font-medium py-1.5 whitespace-nowrap">
                      {new Date(game.game_date).toLocaleDateString(locale, {
                        month: "short",
                        day: "numeric",
                      })}
                    </TableCell>
                    <TableCell className="py-1.5">
                      <span className="flex items-center text-muted-foreground gap-1">
                        {game.is_home ? "vs" : "@"}
                        <TeamLogo team={game.opponent} size={LOGO_SIZE} />
                      </span>
                    </TableCell>
                    <TableCell className="text-right py-1.5">
                      <ScoreBadge score={game.fantasy_score} dnp={game.dnp} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Right: Chart + Performance Insights stacked */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{t("scoreTrend")}</CardTitle>
              <CardDescription className="text-sm">
                {t("average", { value: data.avg_fantasy.toFixed(1) })}
              </CardDescription>
            </CardHeader>
            <CardContent className="pb-4">
              <ScoreChart games={playedGames} avgScore={data.avg_fantasy} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{t("insights")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 pb-4">
              <div className="flex items-start gap-2.5">
                <div className="bg-primary/10 rounded-full p-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-sm">{t("avgPerformance")}</p>
                  <p className="text-sm text-muted-foreground">
                    {data.avg_fantasy >= 45
                      ? t("avgPerfElite")
                      : data.avg_fantasy >= 35
                        ? t("avgPerfSolid")
                        : t("avgPerfDeveloping")}
                  </p>
                </div>
              </div>
              {pickedGames.length > 0 && (
                <div className="flex items-start gap-2.5">
                  <div className="bg-green-500/10 rounded-full p-1.5">
                    <Target className="h-3.5 w-3.5 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{t("pickHistory")}</p>
                    <p className="text-sm text-muted-foreground">
                      {t("pickHistoryText", {
                        count: pickedGames.length,
                        avg: avgPicked,
                      })}
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-2.5">
                <div className="bg-purple-500/10 rounded-full p-1.5">
                  <Trophy className="h-3.5 w-3.5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium text-sm">{t("consistencyRating")}</p>
                  <p className="text-sm text-muted-foreground">
                    {consistency === "High"
                      ? t("consistencyHigh")
                      : consistency === "Medium"
                        ? t("consistencyMedium")
                        : t("consistencyLow")}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
