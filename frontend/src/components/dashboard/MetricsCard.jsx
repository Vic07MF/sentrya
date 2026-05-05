"use client";

import { Activity, Thermometer } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { IconBox } from "@/components/ui/IconBox";
import { Skeleton } from "@/components/ui/Skeleton";

const METRICS = [
  {
    key: "vibracao",
    label: "Vibração",
    icon: Activity,
    color: "text-status-danger",
    iconVariant: "danger",
    format: (v) => String(v),
  },
  {
    key: "temperatura",
    label: "Temperatura",
    icon: Thermometer,
    color: "text-status-warn",
    iconVariant: "warn",
    format: (v) => `${v}°`,
  },
];

export function MetricsCard({ vibracao, temperatura }) {
  const values = { vibracao, temperatura };

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <IconBox variant="info">◈</IconBox>
        <span className="text-[11px] font-semibold uppercase tracking-[.08em] text-brand-muted">
          Métricas em Tempo Real
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        {METRICS.map(
          ({ key, label, icon: Icon, color, iconVariant, format }) => (
            <div
              key={key}
              className="flex items-center gap-2.5 rounded-xl border border-accent/25 bg-white/[0.02] p-3"
            >
              <IconBox variant={iconVariant} className="shrink-0">
                <Icon size={13} className={color} />
              </IconBox>
              <div>
                {values[key] == null ? (
                  <Skeleton className="h-5 w-10" />
                ) : (
                  <div className="font-mono text-lg font-bold leading-none text-brand-cream">
                    {format(values[key])}
                  </div>
                )}
                <div className="mt-1 font-mono text-[10px] uppercase tracking-[.06em] text-brand-muted">
                  {label}
                </div>
              </div>
            </div>
          ),
        )}
      </div>
    </Card>
  );
}
