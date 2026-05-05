"use client";

import { TrendingUp } from "lucide-react";
import { Card }    from "@/components/ui/Card";
import { IconBox } from "@/components/ui/IconBox";
import { Skeleton } from "@/components/ui/Skeleton";
import { getInsightMessage, isAnomaly, formatPercent } from "@/lib/utils";

export function InsightCard({ data }) {
  const loading  = !data;
  const anomaly  = data ? isAnomaly(data.vibracao) : false;
  const headline = data ? getInsightMessage(data.vibracao) : "";

  return (
    <Card className="p-5">
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <IconBox variant="info">
          <TrendingUp size={14} className="text-accent-light" />
        </IconBox>
        <span className="text-[11px] font-semibold uppercase tracking-[.08em] text-brand-muted">
          Insight
        </span>
      </div>

      {/* Headline */}
      {loading ? (
        <Skeleton className="mb-1.5 h-6 w-3/4" />
      ) : (
        <h3 className="mb-1.5 text-lg font-bold leading-tight text-brand-cream">
          {headline}
        </h3>
      )}

      {/* Delta */}
      <div className="mb-4 flex items-center gap-1.5 font-mono text-xs text-status-warn">
        <svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current stroke-2">
          <polyline points="18 15 12 9 6 15" />
        </svg>
        {loading ? (
          <Skeleton className="h-3 w-32" />
        ) : (
          `Risco estimado: ${formatPercent(data.risk_pct)} — ao vivo`
        )}
      </div>

      {/* Risk row */}
      <div className="flex items-start gap-2.5 border-b border-accent/20 py-2.5">
        <IconBox variant="warn" className="mt-0.5">⚠</IconBox>
        <div>
          <p className="text-[13px] font-semibold text-brand-cream">
            Risco de falha em curto prazo
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-brand-muted">
            Probabilidade de falha:{" "}
            <span className="text-status-warn">
              {loading ? "—" : formatPercent(data.risk_pct)}
            </span>
          </p>
        </div>
      </div>

      {/* Recommendation row */}
      <div className="flex items-start gap-2.5 pt-2.5">
        <IconBox variant="info" className="mt-0.5">◎</IconBox>
        <div>
          <p className="text-[13px] font-semibold text-brand-cream">
            {anomaly ? "Verificar Rolamento do Motor" : "Monitoramento Contínuo Ativo"}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-brand-muted">
            Recomendação baseada em padrão de vibração
          </p>
        </div>
      </div>
    </Card>
  );
}
