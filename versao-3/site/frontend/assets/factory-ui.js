(function (root) {
  "use strict";
  const pendingEventStates = new Set(["awaiting_capture", "processing", "pending"]);
  const eventLabels = {
    awaiting_capture: "Aguardando fotografia", processing: "Analisando imagem", pending: "Processando",
    recognized: "Reconhecido", unknown: "Não identificado", error: "Erro", cancelled: "Cancelado"
  };
  const commandLabels = {
    pending: "Solicitado — aguardando confirmação", applied: "Confirmado pela placa",
    rejected: "Recusado pela placa", expired: "Expirado", superseded: "Substituído",
    latched: "Parada registrada — aguardando conexão"
  };
  const actionLabels = { calibrate: "Calibrar", start: "Iniciar", stop: "Parar" };

  function controls(factory, context = {}) {
    const authenticated = context.authenticated === true;
    const available = authenticated && !context.preview && context.serverOnline === true;
    const motor = factory?.motor || {};
    const telemetry = motor.telemetry || {};
    const pending = pendingEventStates.has(factory?.event?.status);
    const stopped = telemetry.motor_on === false;
    const base = available && motor.online === true && stopped && telemetry.sensor_valid === true && !pending && !context.commandBusy;
    const aiReady = factory?.ai?.online === true && factory.ai.status === "ready";
    return {
      calibrate: base && factory?.can_calibrate === true,
      start: base && factory?.can_start === true && telemetry.calibrated === true && telemetry.area_clear === true && factory?.camera?.online === true && aiReady,
      // A parada pode ser solicitada mesmo sem telemetria ou com erro de conexão.
      stop: authenticated && !context.preview && !context.stopBusy
    };
  }

  function eventLabel(value) { return eventLabels[value] || value || "Aguardando peça"; }
  function commandLabel(value) { return commandLabels[value] || value || "Sem comando"; }
  function actionLabel(value) { return actionLabels[value] || value || "—"; }
  const api = { controls, eventLabel, commandLabel, actionLabel };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FactoryUI = api;
})(typeof window !== "undefined" ? window : globalThis);
