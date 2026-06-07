"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { usePicks } from "@/lib/core/hooks/usePicks";
import { parseAndMatchTTFLData } from "@/lib/core/domain/import";
import { AlertCircle, CheckCircle2, Upload, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

interface ImportPicksProps {
  onImportComplete: () => void;
  onClose: () => void;
}

export default function ImportPicks({
  onImportComplete,
  onClose,
}: ImportPicksProps) {
  const t = useTranslations("Import");
  const { importMany } = usePicks();
  const [tsvData, setTsvData] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    imported: number;
    skipped: number;
    unmatched: string[];
    error?: string;
  } | null>(null);

  const errorMessage = (code: "no_data" | "no_match" | "unknown") =>
    code === "no_data"
      ? t("errorNoData")
      : code === "no_match"
        ? t("errorNoMatch")
        : t("errorUnknown");

  const handleImport = async () => {
    if (!tsvData.trim()) {
      setResult({
        success: false,
        imported: 0,
        skipped: 0,
        unmatched: [],
        error: t("errorEmpty"),
      });
      return;
    }

    try {
      setLoading(true);
      setResult(null);

      // Parse and match player names
      const { picks, unmatched, error } = await parseAndMatchTTFLData(tsvData);

      if (error) {
        setResult({
          success: false,
          imported: 0,
          skipped: 0,
          unmatched,
          error: errorMessage(error),
        });
        return;
      }

      // Persist matched picks to the backend
      const { imported, skipped } = await importMany(
        picks.map((p) => ({ playerId: p.playerId, date: p.date }))
      );

      setResult({
        success: true,
        imported,
        skipped,
        unmatched,
      });

      // Refresh the parent component and close modal after a short delay
      setTimeout(() => {
        onImportComplete();
        onClose();
      }, 1500);
    } catch (err) {
      setResult({
        success: false,
        imported: 0,
        skipped: 0,
        unmatched: [],
        error: t("errorUnknown"),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              {t("title")}
            </CardTitle>
            <CardDescription className="mt-2">
              {t("description")}
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="shrink-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Instructions */}
          <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
            <p className="font-medium">{t("howTo")}</p>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>
                {t("step1Before")}
                <a
                  href="https://fantasy.trashtalk.co/?tpl=historique"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  {t("step1Link")}
                </a>
                {t("step1After")}
              </li>
              <li>{t("step2")}</li>
              <li>{t("step3")}</li>
            </ol>
            <p className="text-xs text-muted-foreground mt-2">{t("note")}</p>
          </div>

          {/* Textarea */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              {t("pasteLabel")}
            </label>
            <textarea
              value={tsvData}
              onChange={(e) => setTsvData(e.target.value)}
              placeholder="Date	Joueur	Pts	Reb	Ast	Stl	Blk	Ftm	Fgm	Fg3m	Malus	Score
2025-10-21	Shai Gilgeous-Alexander	35	5	5	2	2	10	12	1	29	43
2025-10-22	Cade Cunningham	23	7	10	1	0	6	8	1	28	28"
              className="w-full h-48 p-3 text-sm font-mono bg-background border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={loading}
            />
          </div>

          {/* Result */}
          {result && (
            <div
              className={`rounded-lg p-4 ${
                result.success
                  ? "bg-green-500/10 border border-green-500/20"
                  : "bg-destructive/10 border border-destructive/20"
              }`}
            >
              <div className="flex items-start gap-3">
                {result.success ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                )}
                <div className="space-y-1 flex-1">
                  <p className="font-medium">
                    {result.success ? t("success") : t("failed")}
                  </p>
                  {result.success ? (
                    <>
                      <p className="text-sm text-muted-foreground">
                        {t("imported", { count: result.imported })}
                        {result.skipped > 0 &&
                          t("skipped", { count: result.skipped })}
                      </p>
                      {result.unmatched.length > 0 && (
                        <div className="mt-2">
                          <p className="text-sm font-medium text-amber-600">
                            {t("unmatchedWarning", {
                              count: result.unmatched.length,
                            })}
                          </p>
                          <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                            {result.unmatched.slice(0, 5).map((name, i) => (
                              <li key={i}>• {name}</li>
                            ))}
                            {result.unmatched.length > 5 && (
                              <li>
                                •{" "}
                                {t("andMore", {
                                  count: result.unmatched.length - 5,
                                })}
                              </li>
                            )}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {result.error}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={onClose} disabled={loading}>
              {result?.success ? t("close") : t("cancel")}
            </Button>
            <Button
              onClick={handleImport}
              disabled={loading || !tsvData.trim()}
            >
              {loading ? (
                <>
                  <span className="animate-spin mr-2">⏳</span>
                  {t("importing")}
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  {t("importPicks")}
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
