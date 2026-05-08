"use client";

import { TopNav } from "@/components/layout/TopNav";
import { MachinesList } from "@/components/machines/MachinesList";
import { StatusCard } from "@/components/dashboard/StatusCard";
import { InsightCard } from "@/components/dashboard/InsightCard";
import { VibrationChart } from "@/components/dashboard/VibrationChart";
import { MetricsCard } from "@/components/dashboard/MetricsCard";
import { EventsList } from "@/components/dashboard/EventsList";
import { Card } from "@/components/ui/Card";
import { useSensorData } from "@/hooks/useSensorData";
import { useNavTab } from "@/hooks/useNavTab";
import { isAnomaly } from "@/lib/utils";

export default function DashboardPage() {
  const {
    data,
    history,
    anomalies,
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

        {/* "Histórico" */}
        {active === "Histórico" && (
          <div className="animate-fadeIn">
            <Card className="p-6">
              <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-brand-cream">
                    Histórico de leituras
                  </p>
                  <p className="mt-1 text-xs font-mono text-brand-muted">
                    Exibe os últimos registros carregados do histórico SQLite.
                  </p>
                </div>
                <span className="rounded-full border border-brand-border bg-slate-950/10 px-3 py-1 text-[11px] font-semibold text-brand-muted">
                  {history.length} leituras
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-brand-border text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-brand-border text-brand-muted">
                      <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                        Hora
                      </th>
                      <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                        Vibração
                      </th>
                      <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                        Temperatura
                      </th>
                      <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                        Energia
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-border">
                    {history.length === 0 ? (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-3 py-4 text-sm text-brand-muted"
                        >
                          Nenhum dado histórico disponível no momento.
                        </td>
                      </tr>
                    ) : (
                      history.map((entry, index) => (
                        <tr
                          key={`${entry.timestamp}-${index}`}
                          className="hover:bg-slate-950/10"
                        >
                          <td className="px-3 py-3 font-mono text-xs text-brand-cream">
                            {entry.label}
                          </td>
                          <td className="px-3 py-3 font-mono text-xs text-brand-cream">
                            {Number(entry.value ?? 0).toFixed(2)}
                          </td>
                          <td className="px-3 py-3 font-mono text-xs text-brand-cream">
                            {Number(entry.temperatura ?? 0).toFixed(2)}
                          </td>
                          <td className="px-3 py-3 font-mono text-xs text-brand-cream">
                            {Number(entry.energia ?? 0).toFixed(2)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Anomalias Detectadas */}
              <div className="mt-8">
                <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-red-400">
                      Anomalias Detectadas pela IA
                    </p>
                    <p className="mt-1 text-xs font-mono text-brand-muted">
                      Eventos de anomalia identificados pelo Isolation Forest em
                      tempo real.
                    </p>
                  </div>
                  <span className="rounded-full border border-red-500/20 bg-red-950/10 px-3 py-1 text-[11px] font-semibold text-red-400">
                    {anomalies.length} anomalias
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-red-500/20 text-left text-[13px]">
                    <thead>
                      <tr className="border-b border-red-500/20 text-red-400">
                        <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                          Timestamp
                        </th>
                        <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                          Vibração
                        </th>
                        <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                          Temperatura
                        </th>
                        <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                          Score
                        </th>
                        <th className="px-3 py-3 font-mono uppercase tracking-[.16em]">
                          Nível
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-red-500/20">
                      {anomalies.length === 0 ? (
                        <tr>
                          <td
                            colSpan={5}
                            className="px-3 py-4 text-sm text-brand-muted"
                          >
                            Nenhuma anomalia detectada ainda.
                          </td>
                        </tr>
                      ) : (
                        anomalies.map((anomaly, index) => (
                          <tr
                            key={`${anomaly.timestamp}-${index}`}
                            className="hover:bg-red-950/5"
                          >
                            <td className="px-3 py-3 font-mono text-xs text-red-300">
                              {anomaly.formattedTime}
                            </td>
                            <td className="px-3 py-3 font-mono text-xs text-red-300">
                              {Number(
                                anomaly.sensor_data?.vib_rms ?? 0,
                              ).toFixed(2)}
                            </td>
                            <td className="px-3 py-3 font-mono text-xs text-red-300">
                              {Number(anomaly.sensor_data?.temp ?? 0).toFixed(
                                2,
                              )}
                            </td>
                            <td className="px-3 py-3 font-mono text-xs text-red-300">
                              {(anomaly.anomaly_score * 100).toFixed(1)}%
                            </td>
                            <td className="px-3 py-3">
                              <span
                                className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                                  anomaly.level === "CRÍTICO"
                                    ? "bg-red-500/20 text-red-400"
                                    : anomaly.level === "ALTO"
                                      ? "bg-orange-500/20 text-orange-400"
                                      : "bg-yellow-500/20 text-yellow-400"
                                }`}
                              >
                                {anomaly.level}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
