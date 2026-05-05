"use client";

import { useState, useEffect, useRef } from "react";
import { formatTime } from "@/lib/utils";
import { startSimulation as startSimulationApi } from "@/services/sensorApi";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/api/v1/ws";
const MAX_HISTORY = 60;
const RECONNECT_MAX_DELAY = 10000;
const INITIAL_RECONNECT_DELAY = 1000;

export function useSensorData() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
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
              energia: fresh.energia,
              timestamp: new Date().toISOString(),
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

  const startSimulation = async () => {
    if (started) return;

    setStartLoading(true);
    setError(null);

    try {
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
    loading,
    error,
    isConnected,
    started,
    startLoading,
    startSimulation,
    maxHistory: MAX_HISTORY,
  };
}
