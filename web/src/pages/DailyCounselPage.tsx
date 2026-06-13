import { useCallback, useEffect, useState } from "react";
import { Activity, ListChecks, Moon, Pause, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { AdvisorErrorLog, ErrorLogEntry, OperatorHealth } from "@/lib/api";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePageHeader } from "@/contexts/usePageHeader";

type Tone = "secondary" | "success" | "warning" | "destructive";

function agoFromEpoch(sec: number | null | undefined): string {
  if (!sec) return "—";
  const diff = Date.now() / 1000 - sec;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function statusTone(status: string | undefined): Tone {
  switch (status) {
    case "working":
      return "success";
    case "paused":
      return "warning";
    case "idle":
      return "secondary";
    default:
      return "secondary";
  }
}

// --------------------------------------------------------------------------- //
// 24/7 daemon health
// --------------------------------------------------------------------------- //
function HealthCard({ data }: { data: OperatorHealth | null }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">24/7 Operator</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground">
          The always-on daemon is active only when there's real work — it idles cheaply otherwise
          and honours the kill-switch. Pause it any time with{" "}
          <span className="font-mono">xavani operator pause</span>.
        </p>
      </CardHeader>
      <CardContent>
        {!data ? (
          <p className="text-sm text-muted-foreground">Loading daemon status…</p>
        ) : data.error ? (
          <p className="text-sm text-destructive">{data.error}</p>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <span className="flex items-center gap-2">
                Status:
                <Badge tone={statusTone(data.status)} className="text-[10px]">
                  {data.status}
                </Badge>
              </span>
              <span className="text-muted-foreground">Cycles run: {data.cycle_count ?? 0}</span>
              <span className="text-muted-foreground">Results produced: {data.acted ?? 0}</span>
              <span className="text-muted-foreground">
                Last tick: {agoFromEpoch(data.last_tick)}
              </span>
            </div>
            {data.paused && (
              <div className="flex items-start gap-2 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
                <Pause className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Paused{data.pause_reason ? ` — ${data.pause_reason}` : ""}. Resume with{" "}
                  <span className="font-mono">xavani operator resume</span>.
                </span>
              </div>
            )}
            {data.status === "never-started" && (
              <p className="text-xs text-muted-foreground">
                The daemon hasn't run yet. Start it with{" "}
                <span className="font-mono">xavani operator serve</span> (or install the launchd /
                systemd service under <span className="font-mono">packaging/</span>).
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// 8pm error log
// --------------------------------------------------------------------------- //
function Section({ title, rows, keys }: { title: string; rows?: Array<Record<string, string>>; keys: [string, string] }) {
  if (!rows || rows.length === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h4>
      <ul className="flex flex-col gap-1 text-sm">
        {rows.map((r, i) => (
          <li key={i} className="text-foreground/90">
            <span className="text-foreground">{r[keys[0]] || "—"}</span>
            {r[keys[1]] ? <span className="text-muted-foreground"> → {r[keys[1]]}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ErrorLogEntryCard({ entry }: { entry: ErrorLogEntry }) {
  const empty =
    !entry.predictions_missed?.length &&
    !entry.beliefs_revised?.length &&
    !entry.wasted_effort?.length &&
    !entry.tomorrow_plan?.length;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{entry.date || "Undated"}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {empty ? (
          <p className="text-sm text-muted-foreground">Logged, but no specifics recorded.</p>
        ) : (
          <>
            <Section title="Predictions that missed" rows={entry.predictions_missed} keys={["predicted", "actual"]} />
            <Section title="Beliefs I revised" rows={entry.beliefs_revised} keys={["believed", "corrected"]} />
            <Section title="Effort wasted on a wrong assumption" rows={entry.wasted_effort} keys={["assumption", "cost"]} />
            <Section title="Tomorrow's plan" rows={entry.tomorrow_plan} keys={["task", "why"]} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function RitualCard({ data }: { data: AdvisorErrorLog | null }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Moon className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">The 8pm error log</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground">
          Every evening I ask four questions — not a diary, a debugging log for your judgment. Your
          answers train the Oracle to spot the mistakes you make more than once.
        </p>
      </CardHeader>
      <CardContent>
        <ol className="ml-4 list-decimal text-sm text-foreground/90">
          {(data?.questions ?? [
            "What did you predict today that didn't happen?",
            "What did you believe yesterday that turned out to be off?",
            "Where did you waste effort because an assumption was wrong?",
            "What's your plan for tomorrow — the tasks you want done?",
          ]).map((q, i) => (
            <li key={i} className="py-0.5">
              {q}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// Page
// --------------------------------------------------------------------------- //
export default function DailyCounselPage() {
  const [health, setHealth] = useState<OperatorHealth | null>(null);
  const [log, setLog] = useState<AdvisorErrorLog | null>(null);
  const [loading, setLoading] = useState(true);
  const { setEnd } = usePageHeader();

  const load = useCallback(() => {
    setLoading(true);
    Promise.allSettled([api.getOperatorHealth(), api.getAdvisorErrorLog()])
      .then(([h, l]) => {
        if (h.status === "fulfilled") setHealth(h.value);
        else setHealth({ error: String(h.reason) });
        if (l.status === "fulfilled") setLog(l.value);
        else setLog({ error: String(l.reason) });
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setEnd(
      <Button type="button" size="sm" outlined onClick={load} disabled={loading} prefix={loading ? <Spinner /> : <RefreshCw />}>
        Refresh
      </Button>,
    );
    return () => setEnd(null);
  }, [load, loading, setEnd]);

  const entries = log?.entries ?? [];

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted-foreground">
        Your daily counsel: how the 24/7 operator is doing, the evening error-log ritual, and the
        history of what you've learned from being wrong.
      </p>
      <HealthCard data={health} />
      <RitualCard data={log} />
      {log?.error ? (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{log.error}</p>
          </CardContent>
        </Card>
      ) : entries.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center text-center text-muted-foreground">
              <ListChecks className="mb-3 h-8 w-8 opacity-40" />
              <p className="text-sm font-medium">No error-log entries yet</p>
              <p className="mt-1 text-xs text-muted-foreground/60">
                At 8pm I'll ask about your day; your answers appear here as a timeline.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          <h3 className="text-sm font-semibold text-foreground">Error-log timeline</h3>
          {entries.map((e, i) => (
            <ErrorLogEntryCard key={`${e.date}-${i}`} entry={e} />
          ))}
        </div>
      )}
    </div>
  );
}
