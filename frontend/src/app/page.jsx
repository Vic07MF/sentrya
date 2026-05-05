"use client";

import { TopNav } from "@/components/layout/TopNav";
import { MachinesList } from "@/components/machines/MachinesList";
import { StatusCard } from "@/components/dashboard/StatusCard";
import { InsightCard } from "@/components/dashboard/InsightCard";
import { VibrationChart } from "@/components/dashboard/VibrationChart";
import { MetricsCard } from "@/components/dashboard/MetricsCard";
import { EventsList } from "@/components/dashboard/EventsList";
import { useSensorData } from "@/hooks/useSensorData";
import { useNavTab } from "@/hooks/useNavTab";
import { isAnomaly } from "@/lib/utils";

export default function DashboardPage() {
  const {
    data,
    history,
    loading,
    error,
    isConnected,
    started,
    startLoading,
    startSimulation,
  } = useSensorData();

  const { active } = useNavTab();

  const anomaly = data
    ? data.status === "ALERTA" || data.status === "CRITICO"
    : false;

  return (
    <div className="flex min-h-screen flex-col bg-bg-primary">
      <TopNav />

      {/* Only show header and test button on "Visão Geral" tab */}
      {active === "Visão Geral" && (
        <div className="border-b border-brand-border bg-slate-950/10 px-6 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-mono text-brand-muted">
                Inicie o teste das máquinas simuladas para receber vibração e
                temperatura em tempo real.
              </p>
              <p className="text-xs font-mono text-brand-cream">
                Atualização em tempo real por segundo assim que a simulação for
                ativada.
              </p>
            </div>
            <button
              onClick={startSimulation}
              disabled={started || startLoading}
              className="inline-flex items-center justify-center rounded-full border border-brand-border bg-brand-cream px-4 py-2 text-[12px] font-semibold text-slate-950 transition hover:bg-brand-cream/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {started
                ? "Simulação ativa"
                : startLoading
                  ? "Iniciando teste..."
                  : "Iniciar teste"}
            </button>
          </div>
        </div>
      )}

      {/* Connection Status Indicator */}
      {!isConnected && active === "Visão Geral" && (
        <div className="border-b border-brand-border bg-red-950/20 px-6 py-2">
          <p className="text-xs font-mono text-red-400">
            {error || "⚠️ Desconectado do servidor - reconectando..."}
          </p>
        </div>
      )}

      {isConnected && active === "Visão Geral" && (
        <div className="border-b border-brand-border bg-green-950/10 px-6 py-1.5">
          <p className="text-xs font-mono text-green-400">
            ✓ Conectado em tempo real
          </p>
        </div>
      )}

      <main className="flex-1 p-6">
        {/* "Visão Geral" - Dashboard grid view */}
        {active === "Visão Geral" && (
          <div className="grid grid-cols-2 gap-4">
            {/* ── Left column ──────────────────────────────── */}

            {/* Status */}
            <div className="animate-fadeIn" style={{ animationDelay: "0ms" }}>
              <StatusCard data={data} loading={loading} />
            </div>

            {/* Insight */}
            <div className="animate-fadeIn" style={{ animationDelay: "80ms" }}>
              <InsightCard data={data} />
            </div>

            {/* Vibration chart */}
            <div className="animate-fadeIn" style={{ animationDelay: "160ms" }}>
              <VibrationChart
                history={history}
                isAnomaly={anomaly}
                status={data?.status}
              />
            </div>

            {/* ── Right column (metrics + events stacked) ── */}
            <div
              className="flex animate-fadeIn flex-col gap-4"
              style={{ animationDelay: "240ms" }}
            >
              <MetricsCard
                vibracao={data?.vibracao ?? null}
                temperatura={data?.temperatura ?? null}
              />
              <EventsList events={data?.events ?? []} />
            </div>
          </div>
        )}

        {/* "Máquinas" - Machines list view */}
        {active === "Máquinas" && (
          <div className="animate-fadeIn">
            <MachinesList />
          </div>
        )}

        {/* "Histórico" - Placeholder */}
        {active === "Histórico" && (
          <div className="rounded-lg border border-brand-border bg-card p-6 text-center">
            <p className="font-mono text-sm text-brand-muted">
              Histórico de eventos em desenvolvimento...
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
