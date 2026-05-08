"use client";

import { useState, useEffect, useRef } from "react";
import { formatTime } from "@/lib/utils";
import {
  startSimulation as startSimulationApi,
  getHistory,
  getAnomalyHistory,
} from "@/services/sensorApi";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/api/v1/ws";
const MAX_HISTORY = 60;
const RECONNECT_MAX_DELAY = 10000;
const INITIAL_RECONNECT_DELAY = 1000;

export function useSensorData() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [started, setStarted] = useState(false);
  const [startLoading, setStartLoading] = useState(false);

  const historyRef = useRef([]);
  const tickRef = useRef(0);
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  const calculateReconnectDelay = () => {
    const delay = Math.min(
      INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectCountRef.current),
      RECONNECT_MAX_DELAY,
    );
    return delay;
  };

  const connect = useRef(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`✅ WebSocket conectado em ${WS_URL}`);
        setIsConnected(true);
        setError(null);
        reconnectCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const fresh = JSON.parse(event.data);
          setData(fresh);
          setLoading(false);

          const label = formatTime();
          tickRef.current++;

          const next = [
            ...historyRef.current,
            {
              label,
              value: fresh.vibracao || 0,
              temperatura: fresh.temperatura,
              energia:
                fresh.energia ?? (fresh.vibracao ? fresh.vibracao ** 2 : 0),
              timestamp: fresh.timestamp
                ? new Date(fresh.timestamp).toISOString()
                : new Date().toISOString(),
            },
          ].slice(-MAX_HISTORY);

          historyRef.current = next;
          setHistory(next.map((p) => ({ ...p })));
        } catch (err) {
          console.error("❌ Erro ao parsear mensagem:", err);
        }
      };

      ws.onerror = (err) => {
        console.error("❌ WebSocket erro:", err);
        setIsConnected(false);
        setError("Erro na conexão WebSocket");
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (!started) return;

        reconnectCountRef.current++;
        const delay = calculateReconnectDelay();
        console.warn(
          `⚠️ WebSocket desconectado. Reconectando em ${delay}ms (tentativa ${reconnectCountRef.current})`,
        );

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          connect.current();
        }, delay);
      };
    } catch (err) {
      console.error("❌ Erro ao criar WebSocket:", err);
      setError("Erro ao conectar ao servidor");

      reconnectCountRef.current++;
      const delay = calculateReconnectDelay();

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      reconnectTimeoutRef.current = setTimeout(() => {
        connect.current();
      }, delay);
    }
  });

  const fetchHistory = async () => {
    try {
      const [historyResponse, anomaliesResponse] = await Promise.all([
        getHistory(MAX_HISTORY),
        getAnomalyHistory(20),
      ]);

      if (
        historyResponse.status === "ok" &&
        Array.isArray(historyResponse.data)
      ) {
        const rows = historyResponse.data.reverse();
        const formatted = rows.map((row) => {
          const timestamp = row.timestamp
            ? new Date(row.timestamp)
            : new Date();
          const vibration = Number(row.vibration_rms ?? 0);
          return {
            label: formatTime(timestamp),
            value: vibration,
            temperatura: Number(row.temp ?? 0),
            energia: Number(row.energia ?? vibration ** 2),
            timestamp: timestamp.toISOString(),
          };
        });

        const historyPoints = formatted.slice(-MAX_HISTORY);
        historyRef.current = historyPoints;
        setHistory(historyPoints.map((p) => ({ ...p })));

        if (historyPoints.length > 0) {
          const latest = historyPoints[historyPoints.length - 1];
          const latestRow = rows[rows.length - 1];
          setData({
            vibracao: latest.value,
            temperatura: latest.temperatura,
            energia: latest.energia,
            sensor_id: latestRow.sensor_id,
            status: latestRow.status,
            label: latestRow.label || "normal",
            fault_type: latestRow.label || "normal",
            risk_pct: Math.round(
              (Number(latestRow.anomaly_score ?? 0) || 0) * 100,
            ),
            is_anomaly: String(latestRow.label || "normal") === "anomalia",
            anomaly_score: Number(latestRow.anomaly_score ?? 0),
            timestamp: latest.timestamp,
            events: [],
          });
        }
      }

      // Processa anomalias
      if (
        anomaliesResponse.status === "ok" &&
        Array.isArray(anomaliesResponse.data)
      ) {
        const formattedAnomalies = anomaliesResponse.data.map((anomaly) => ({
          ...anomaly,
          timestamp: new Date(anomaly.timestamp),
          formattedTime: formatTime(new Date(anomaly.timestamp)),
        }));
        setAnomalies(formattedAnomalies);
      }
    } catch (err) {
      console.error("Erro ao buscar dados históricos:", err);
      setError("Falha ao carregar dados históricos");
    } finally {
      setLoading(false);
    }
  };

  const startSimulation = async () => {
    if (started) return;

    setStartLoading(true);
    setError(null);

    try {
      await fetchHistory();
      const response = await startSimulationApi();
      if (response.status === "ok") {
        setStarted(true);
        connect.current();
      } else {
        setError(response.message || "Falha ao iniciar simulação");
      }
    } catch (err) {
      console.error(err);
      setError("Falha ao iniciar simulação");
    } finally {
      setStartLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, []);

  return {
    data,
    history,
    anomalies,
    loading,
    error,
    isConnected,
    started,
    startLoading,
    startSimulation,
    maxHistory: MAX_HISTORY,
  };
}
