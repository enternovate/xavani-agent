import { useCallback, useEffect, useState } from "react";
import { Atom, Brain, Cpu, RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { QuantumPreview, RouterResolved, WisdomVerdict } from "@/lib/api";
import { Button } from "@xavani/ui/ui/components/button";
import { Spinner } from "@xavani/ui/ui/components/spinner";
import { Badge } from "@xavani/ui/ui/components/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePageHeader } from "@/contexts/usePageHeader";

const TASK_LABELS: Record<string, string> = {
  judgment: "Judgment (emails, advice, decisions)",
  code: "Code",
  quick: "Quick (classify, route, extract)",
  vision: "Vision",
  long_context: "Long context",
  bulk: "Bulk (high volume, cheap)",
};

function pct(n: number | undefined): string {
  return `${Math.round((n ?? 0) * 100)}%`;
}

/** Color a 0..1 risk: low = success, mid = warning, high = destructive. */
function riskTone(risk: number): string {
  if (risk >= 0.55) return "text-destructive";
  if (risk >= 0.3) return "text-amber-400";
  return "text-emerald-400";
}

// --------------------------------------------------------------------------- //
// Quantum Decision — the collapse waveform
// --------------------------------------------------------------------------- //
function QuantumCard({ data }: { data: QuantumPreview | null }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Atom className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">Quantum Decision Cortex</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground">
          Candidate strategies held in superposition, their outcomes simulated, correlated risks
          interfered, then collapsed (Born rule) to the best move — deterministic, zero model calls.
        </p>
      </CardHeader>
      <CardContent>
        {!data ? (
          <p className="text-sm text-muted-foreground">Loading the latest decision…</p>
        ) : data.error ? (
          <p className="text-sm text-destructive">{data.error}</p>
        ) : (
          <div className="flex flex-col gap-3">
            {(data.branches ?? []).map((b) => {
              const chosen = b.id === data.chosen;
              return (
                <div key={b.id} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <span className={chosen ? "font-semibold text-foreground" : "text-foreground/80"}>
                        {b.id}
                      </span>
                      {chosen && (
                        <Badge tone="secondary" className="text-[10px]">
                          chosen
                        </Badge>
                      )}
                    </span>
                    <span className="font-mono-ui text-xs text-muted-foreground">
                      p={pct(b.probability)} · ev={b.expected_value.toFixed(2)} ·{" "}
                      <span className={riskTone(b.risk)}>risk={b.risk.toFixed(2)}</span>
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded bg-secondary/40">
                    <div
                      className={chosen ? "h-full bg-primary" : "h-full bg-primary/40"}
                      style={{ width: pct(b.probability) }}
                    />
                  </div>
                  {b.signals.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-0.5">
                      {b.signals.map((s) => (
                        <span
                          key={s}
                          className="rounded bg-destructive/15 px-1.5 py-0.5 text-[10px] text-destructive"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            <p className="pt-1 text-xs text-muted-foreground">
              Note how the highest-scoring option does not always win: the Cortex steers away from
              moves that carry known downfall signals (leverage, overextension, base-rate denial).
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// The Oracle — consequence verdict for any plan you type
// --------------------------------------------------------------------------- //
function OracleCard() {
  const [text, setText] = useState(
    "Borrow heavily, go all in, scale fast — we cannot lose.",
  );
  const [verdict, setVerdict] = useState<WisdomVerdict | null>(null);
  const [loading, setLoading] = useState(false);

  const weigh = useCallback(() => {
    setLoading(true);
    api
      .getWisdomVerdict(text)
      .then(setVerdict)
      .catch((err) => setVerdict({ error: String(err) }))
      .finally(() => setLoading(false));
  }, [text]);

  useEffect(() => {
    weigh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">The Oracle — consequence check</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground">
          Describe a plan or decision. The Oracle projects its consequences and flags the patterns
          that toppled the great (Solomon's overreach, leverage blowups, fraud, hubris).
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
          className="w-full resize-y rounded border border-border bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
          placeholder="e.g. Take on debt to expand into three new markets this quarter."
          aria-label="Plan or decision to weigh"
        />
        <div>
          <Button type="button" size="sm" onClick={weigh} disabled={loading} prefix={loading ? <Spinner /> : <Brain />}>
            Weigh it
          </Button>
        </div>
        {verdict && !verdict.error && (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-4 text-sm">
              <span>
                Risk: <span className={`font-semibold ${riskTone(verdict.risk ?? 0)}`}>{pct(verdict.risk)}</span>
              </span>
              <span className="text-muted-foreground">Expected value: {pct(verdict.expected_value)}</span>
              <span className="text-muted-foreground">Reversibility: {pct(verdict.reversibility)}</span>
              {verdict.base_rate_flag && <span className="text-destructive">base-rate denial detected</span>}
            </div>
            {(verdict.downfall_signals ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1">
                {verdict.downfall_signals!.map((s) => (
                  <span key={s} className="rounded bg-destructive/15 px-1.5 py-0.5 text-[11px] text-destructive">
                    {s}
                  </span>
                ))}
              </div>
            )}
            {(verdict.findings ?? []).length > 0 && (
              <ul className="list-disc pl-5 text-xs text-muted-foreground">
                {verdict.findings!.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            )}
            {(verdict.downfall_signals ?? []).length === 0 && (
              <p className="text-xs text-emerald-400">No known downfall pattern detected — proceed with normal care.</p>
            )}
          </div>
        )}
        {verdict?.error && <p className="text-sm text-destructive">{verdict.error}</p>}
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// Model Router — best model per task by the keys you've set
// --------------------------------------------------------------------------- //
function RouterCard({ data }: { data: RouterResolved | null }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Cpu className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">Model Router</CardTitle>
        </div>
        <p className="text-xs text-muted-foreground">
          The best available model for each kind of task, chosen from the provider API keys you've
          set. Add a key under Keys and the router re-resolves automatically.
        </p>
      </CardHeader>
      <CardContent>
        {!data ? (
          <p className="text-sm text-muted-foreground">Loading routing table…</p>
        ) : data.error ? (
          <p className="text-sm text-destructive">{data.error}</p>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Active providers:</span>
              {(data.available_providers ?? []).length === 0 ? (
                <span className="text-amber-400">none — set a provider API key under Keys</span>
              ) : (
                data.available_providers!.map((p) => (
                  <Badge key={p} tone="secondary" className="text-[10px]">
                    {p}
                  </Badge>
                ))
              )}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Task</th>
                  <th className="py-2 pr-4 font-medium">Model</th>
                  <th className="py-2 font-medium">Provider</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.resolved ?? {}).map(([task, pick]) => (
                  <tr key={task} className="border-b border-border/50">
                    <td className="py-2 pr-4">{TASK_LABELS[task] ?? task}</td>
                    <td className="py-2 pr-4 font-mono-ui text-xs">
                      {pick ? pick.model : <span className="text-muted-foreground">— no model available</span>}
                    </td>
                    <td className="py-2 text-muted-foreground">{pick ? pick.provider : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// Page
// --------------------------------------------------------------------------- //
export default function SentiencePage() {
  const [quantum, setQuantum] = useState<QuantumPreview | null>(null);
  const [router, setRouter] = useState<RouterResolved | null>(null);
  const [loading, setLoading] = useState(true);
  const { setEnd } = usePageHeader();

  const load = useCallback(() => {
    setLoading(true);
    Promise.allSettled([api.getQuantumPreview(), api.getRouterResolved()])
      .then(([q, r]) => {
        if (q.status === "fulfilled") setQuantum(q.value);
        else setQuantum({ error: String(q.reason) });
        if (r.status === "fulfilled") setRouter(r.value);
        else setRouter({ error: String(r.reason) });
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

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted-foreground">
        Xavani's mind, made visible: how it decides (quantum), what it weighs (the Oracle), and
        which model it reaches for (the router). Everything here is computed locally and
        deterministically.
      </p>
      <QuantumCard data={quantum} />
      <OracleCard />
      <RouterCard data={router} />
    </div>
  );
}
