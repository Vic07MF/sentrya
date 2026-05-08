/**
 * Sentrya API Service
 * Serviço para consumo do backend Sentrya em VanillaJS
 *
 * Como usar:
 * 1. Copie este arquivo para o seu projeto frontend
 * 2. Altere a constante API_URL para o endereço do seu backend
 * 3. Use as funções abaixo para consumir os dados
 */

// ============================================
// CONFIGURAÇÃO
// ============================================

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================
// ENDPOINTS DA API
// ============================================

/**
 * Busca todos os sensores ativos
 * @returns {Promise<{status: string, count: number, data: Array}>}
 */
async function getSensores() {
  try {
    const response = await fetch(`${API_URL}/api/v1/sensores`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Erro ao buscar sensores:", error);
    return { status: "error", data: [], count: 0 };
  }
}

/**
 * Busca dados de um sensor específico
 * @param {string} sensorId - ID do sensor (ex: 'MOTOR_1', 'BOMBA_02', 'VENT_03')
 * @returns {Promise<Object>}
 */
async function getSensor(sensorId) {
  try {
    const response = await fetch(`${API_URL}/api/v1/sensores/${sensorId}`);
    if (!response.ok) {
      throw new Error(`Sensor ${sensorId} não encontrado`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Erro ao buscar sensor ${sensorId}:`, error);
    return null;
  }
}

/**
 * Busca todos os alertas ativos
 * @returns {Promise<Array>}
 */
async function getAlertas() {
  try {
    const response = await fetch(`${API_URL}/api/v1/alertas`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Erro ao buscar alertas:", error);
    return [];
  }
}

/**
 * Verifica se o backend está online
 * @returns {Promise<boolean>}
 */
async function checkHealth() {
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();
    return data.status === "healthy";
  } catch (error) {
    console.error("Backend offline:", error);
    return false;
  }
}

/**
 * Busca histórico de registros armazenados em SQLite
 * @param {number} limit
 * @param {string|null} sensorId
 * @returns {Promise<Object>}
 */
async function getHistory(limit = 100, sensorId = null) {
  try {
    const params = new URLSearchParams();
    params.append("limit", String(limit));
    if (sensorId) params.append("sensor_id", sensorId);

    const response = await fetch(
      `${API_URL}/api/v1/dados/sqlite?${params.toString()}`,
    );
    return await response.json();
  } catch (error) {
    console.error("Erro ao buscar histórico:", error);
    return { status: "error", count: 0, data: [] };
  }
}

/**
 * Inicia a simulação de teste no backend
 * @returns {Promise<Object>}
 */
async function startSimulation() {
  try {
    const response = await fetch(`${API_URL}/api/v1/simular/iniciar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return await response.json();
  } catch (error) {
    console.error("Erro ao iniciar simulação:", error);
    return { status: "error", message: "Não foi possível iniciar a simulação" };
  }
}

// ============================================
// WEBSOCKET - DADOS EM TEMPO REAL
// ============================================

let websocket = null;
let wsReconnectInterval = null;
let wsOnMessageCallback = null;
let wsOnConnectCallback = null;
let wsOnDisconnectCallback = null;

/**
 * Conecta ao WebSocket para receber dados em tempo real
 * @param {Function} onMessage - Callback quando receber dados: (dados) => {}
 * @param {Function} onConnect - Callback quando conectar: () => {}
 * @param {Function} onDisconnect - Callback quando desconectar: () => {}
 */
function connectWebSocket(onMessage, onConnect, onDisconnect) {
  wsOnMessageCallback = onMessage;
  wsOnConnectCallback = onConnect;
  wsOnDisconnectCallback = onDisconnect;

  // Converte http:// para ws://
  const wsUrl = API_URL.replace("http://", "ws://") + "/api/v1/ws";

  websocket = new WebSocket(wsUrl);

  websocket.onopen = () => {
    console.log("✅ WebSocket conectado!");
    if (wsOnConnectCallback) wsOnConnectCallback();

    // Limpa intervalo de reconexão se existir
    if (wsReconnectInterval) {
      clearInterval(wsReconnectInterval);
      wsReconnectInterval = null;
    }
  };

  websocket.onmessage = (event) => {
    try {
      const dados = JSON.parse(event.data);
      if (wsOnMessageCallback) wsOnMessageCallback(dados);
    } catch (error) {
      console.error("Erro ao processar dados WebSocket:", error);
    }
  };

  websocket.onclose = () => {
    console.log("❌ WebSocket desconectado");
    if (wsOnDisconnectCallback) wsOnDisconnectCallback();

    // Tenta reconectar após 3 segundos
    wsReconnectInterval = setInterval(() => {
      console.log("🔄 Tentando reconectar WebSocket...");
      connectWebSocket(
        wsOnMessageCallback,
        wsOnConnectCallback,
        wsOnDisconnectCallback,
      );
    }, 3000);
  };

  websocket.onerror = (error) => {
    console.error("Erro no WebSocket:", error);
  };
}

/**
 * Desconecta do WebSocket
 */
function disconnectWebSocket() {
  if (wsReconnectInterval) {
    clearInterval(wsReconnectInterval);
    wsReconnectInterval = null;
  }
  if (websocket) {
    websocket.close();
    websocket = null;
  }
}

/**
 * Envia mensagem via WebSocket (para keepalive)
 */
function sendPing() {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send("ping");
  }
}

// ============================================
// HELPERS - FUNÇÕES AUXILIARES
// ============================================

/**
 * Retorna a cor baseada no status do sensor
 * @param {string} status - Status do sensor
 * @returns {string} - Cor em hexadecimal
 */
function getStatusColor(status) {
  const colors = {
    OK: "#22c55e", // Verde
    ATENCAO: "#eab308", // Amarelo
    ALERTA: "#f97316", // Laranja
    CRITICO: "#ef4444", // Vermelho
    FALHA: "#6b7280", // Cinza
  };
  return colors[status] || "#6b7280";
}

/**
 * Retorna o nível de alerta como texto
 * @param {number} alertLevel - Nível do alerta (0-4)
 * @returns {string}
 */
function getAlertLevelText(alertLevel) {
  const levels = ["OK", "ATENÇÃO", "ALERTA", "CRÍTICO", "FALHA"];
  return levels[alertLevel] || "DESCONHECIDO";
}

/**
 * Formata o timestamp para exibir
 * @param {string} timestamp - Timestamp ISO
 * @returns {string} - Data formatada
 */
function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleString("pt-BR");
}

export {
  getSensores,
  getSensor,
  getAlertas,
  checkHealth,
  getHistory,
  getAnomalyHistory,
  startSimulation,
  connectWebSocket,
  disconnectWebSocket,
  sendPing,
  getStatusColor,
  getAlertLevelText,
  formatTimestamp,
};
