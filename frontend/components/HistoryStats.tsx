"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/web/cn";
import { Award, BarChart2, TrendingDown, TrendingUp } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface PickStat {
  date: string;
  playerName: string;
  fantasyScore?: number | null;
}

interface HistoryStatsProps {
  picks: PickStat[];
}

const BUCKETS = [
  { label: "<5", min: -Infinity, max: 5 },
  { label: "5-9", min: 5, max: 10 },
  { label: "10-14", min: 10, max: 15 },
  { label: "15-19", min: 15, max: 20 },
  { label: "20-24", min: 20, max: 25 },
  { label: "25-29", min: 25, max: 30 },
  { label: "30-34", min: 30, max: 35 },
  { label: "35-39", min: 35, max: 40 },
  { label: "40-44", min: 40, max: 45 },
  { label: "45-49", min: 45, max: 50 },
  { label: "50-54", min: 50, max: 55 },
  { label: "55-59", min: 55, max: 60 },
  { label: "60+", min: 60, max: Infinity },
];

const BUCKET_COLORS = [
  "hsl(0 84% 60%)",
  "hsl(5 88% 59%)",
  "hsl(12 90% 57%)",
  "hsl(22 93% 55%)",
  "hsl(32 94% 52%)",
  "hsl(42 93% 48%)",
  "hsl(60 80% 44%)",
  "hsl(85 70% 42%)",
  "hsl(110 65% 40%)",
  "hsl(130 68% 42%)",
  "hsl(142 70% 45%)",
  "hsl(142 76% 36%)",
  "hsl(158 64% 32%)",
];

function scoreColor(score: number): string {
  if (score >= 50) return "hsl(158 64% 32%)";
  if (score >= 40) return "hsl(142 76% 36%)";
  if (score >= 20) return "var(--foreground)";
  return "hsl(0 84% 60%)";
}

function TimelineTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: { score: number; player: string } }>;
  label?: string;
}) {
  const t = useTranslations("History");
  if (!active || !payload?.length) return null;
  const { score, player } = payload[0].payload;
  return (
    <div className="bg-popover border border-border rounded-lg shadow-xl p-3 min-w-32">
      <p className="text-[10px] text-muted-foreground mb-1 font-medium">
        {label}
      </p>
      <p
        className="font-black text-lg leading-none"
        style={{ color: scoreColor(score) }}
      >
        {t("pts", { score })}
      </p>
      <p className="text-[10px] text-muted-foreground truncate mt-1.5 max-w-32">
        {player}
      </p>
    </div>
  );
}

function DistributionTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  const t = useTranslations("History");
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-popover border border-border rounded-lg shadow-xl p-3">
      <p className="text-[10px] text-muted-foreground mb-1 font-medium">
        {label}
      </p>
      <p className="font-bold text-sm">
        {t("picksCount", { count: payload[0].value })}
      </p>
    </div>
  );
}

interface StatCardProps {
  accentClass: string;
  iconBgClass: string;
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  sub: React.ReactNode;
}

function StatCard({
  accentClass,
  iconBgClass,
  icon,
  label,
  value,
  sub,
}: StatCardProps) {
  return (
    <Card
      className={cn(
        "border-l-4 hover:shadow-lg transition-all duration-300 p-3",
        accentClass
      )}
    >
      <CardHeader className="pb-0 pt-3 px-3 sm:pt-4 sm:px-5">
        <div
          className={cn(
            "inline-flex items-center gap-1.5 w-fit px-1.5 py-0.5 rounded-md",
            iconBgClass
          )}
        >
          {icon}
          <span className="text-[10px] sm:text-[11px] font-semibold text-muted-foreground leading-none">
            {label}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pb-3 px-3 sm:pb-4 sm:px-5 pt-2">
        <div className="text-2xl sm:text-4xl font-black tabular-nums leading-none tracking-tight">
          {value}
        </div>
        <p className="text-[10px] sm:text-xs text-muted-foreground mt-1.5 font-medium truncate">
          {sub}
        </p>
      </CardContent>
    </Card>
  );
}

export function HistoryStats({ picks }: HistoryStatsProps) {
  const t = useTranslations("History");
  const locale = useLocale();

  const scored = picks.filter(
    (p): p is PickStat & { fantasyScore: number } =>
      typeof p.fantasyScore === "number"
  );

  if (scored.length === 0) return null;

  const scores = scored.map((p) => p.fantasyScore);
  const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  const best = scored.reduce((a, b) =>
    b.fantasyScore > a.fantasyScore ? b : a
  );
  const worst = scored.reduce((a, b) =>
    b.fantasyScore < a.fantasyScore ? b : a
  );

  const timeline = [...scored]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((p) => ({
      date: new Date(p.date).toLocaleDateString(locale, {
        month: "short",
        day: "numeric",
      }),
      score: p.fantasyScore,
      player: p.playerName,
    }));

  const yMin = Math.max(0, Math.floor(Math.min(...scores) / 10) * 10 - 10);
  const yMax = Math.ceil(Math.max(...scores) / 10) * 10 + 10;

  const distribution = BUCKETS.map((b) => ({
    label: b.label,
    count: scores.filter((s) => s >= b.min && s < b.max).length,
  }));

  const above40Count = scores.filter((s) => s >= 40).length;
  const above40Pct =
    scored.length > 0
      ? `${Math.round((above40Count / scored.length) * 100)}%`
      : "—";

  return (
    <div className="space-y-5 sm:space-y-6">
      {/* Stat cards — 2×2 on mobile, 4-col on sm+ */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
        <StatCard
          accentClass="border-l-primary"
          iconBgClass="bg-primary/10"
          icon={<TrendingUp className="h-3 w-3 text-primary shrink-0" />}
          label={t("avgScore")}
          value={
            <span className="bg-linear-to-br from-foreground to-foreground/60 bg-clip-text text-transparent">
              {avg}
            </span>
          }
          sub={`${t("scoredPicks")} · ${scored.length}/${picks.length}`}
        />

        <StatCard
          accentClass="border-l-green-500"
          iconBgClass="bg-green-500/10"
          icon={<Award className="h-3 w-3 text-green-600 shrink-0" />}
          label={t("bestScore")}
          value={
            <span className="bg-linear-to-br from-green-600 to-green-500 bg-clip-text text-transparent">
              {best.fantasyScore}
            </span>
          }
          sub={best.playerName}
        />

        <StatCard
          accentClass="border-l-destructive"
          iconBgClass="bg-destructive/10"
          icon={<TrendingDown className="h-3 w-3 text-destructive shrink-0" />}
          label={t("worstScore")}
          value={
            <span className="bg-linear-to-br from-destructive to-destructive/70 bg-clip-text text-transparent">
              {worst.fantasyScore}
            </span>
          }
          sub={worst.playerName}
        />

        <StatCard
          accentClass="border-l-amber-400"
          iconBgClass="bg-amber-400/10"
          icon={<BarChart2 className="h-3 w-3 text-amber-500 shrink-0" />}
          label={t("above40")}
          value={
            <span className="bg-linear-to-br from-amber-600 to-amber-400 bg-clip-text text-transparent">
              {above40Count}
            </span>
          }
          sub={`${above40Pct} ${t("ofPicks")}`}
        />
      </div>

      {/* Charts — stacked on mobile, side-by-side on desktop */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
        {/* Score timeline */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-0 pt-4 px-4 sm:pt-4 sm:px-5">
            <CardTitle className="text-sm font-semibold tracking-tight">
              {t("timelineTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-1 sm:px-2 pb-4 pt-3">
            <div className="h-48 sm:h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={timeline}
                  margin={{ top: 10, right: 12, left: -4, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="historyGradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="var(--primary)"
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="85%"
                        stopColor="var(--primary)"
                        stopOpacity={0.03}
                      />
                      <stop
                        offset="100%"
                        stopColor="var(--primary)"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="var(--border)"
                    strokeOpacity={0.6}
                  />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 9, fill: "var(--muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    tickMargin={6}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: "var(--muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    domain={[yMin, yMax]}
                    tickMargin={4}
                    width={26}
                  />
                  <Tooltip
                    content={<TimelineTooltip />}
                    cursor={{
                      stroke: "var(--muted-foreground)",
                      strokeOpacity: 0.25,
                      strokeDasharray: "4 4",
                    }}
                  />
                  <ReferenceLine
                    y={avg}
                    stroke="var(--muted-foreground)"
                    strokeDasharray="6 4"
                    strokeOpacity={0.45}
                    label={{
                      value: `∅ ${avg}`,
                      position: "insideTopRight",
                      fontSize: 9,
                      fill: "var(--muted-foreground)",
                      fontWeight: 600,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="var(--primary)"
                    strokeWidth={2.5}
                    fill="url(#historyGradient)"
                    dot={{
                      r: 2.5,
                      fill: "var(--primary)",
                      strokeWidth: 0,
                    }}
                    activeDot={{
                      r: 5,
                      fill: "var(--primary)",
                      stroke: "var(--background)",
                      strokeWidth: 2,
                    }}
                    animationDuration={600}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Score distribution */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-0 pt-4 px-4 sm:pt-4 sm:px-5">
            <CardTitle className="text-sm font-semibold tracking-tight">
              {t("distributionTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-1 sm:px-2 pb-4 pt-3">
            <div className="h-40 sm:h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={distribution}
                  margin={{ top: 4, right: 12, left: -4, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="var(--border)"
                    strokeOpacity={0.6}
                  />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 9, fill: "var(--muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    tickMargin={4}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 9, fill: "var(--muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    width={22}
                  />
                  <Tooltip
                    content={<DistributionTooltip />}
                    cursor={{ fill: "var(--muted)", fillOpacity: 0.4 }}
                  />
                  <Bar
                    dataKey="count"
                    radius={[4, 4, 0, 0]}
                    animationDuration={600}
                    maxBarSize={30}
                  >
                    {distribution.map((_, i) => (
                      <Cell key={i} fill={BUCKET_COLORS[i]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
      {/* end charts grid */}
    </div>
  );
}
