const assert = require("node:assert/strict");
const { controls, eventLabel, commandLabel } = require("../assets/factory-ui.js");
const factory = {
  motor: { online: true, telemetry: { motor_on: false, sensor_valid: true, calibrated: true, area_clear: true } },
  camera: { online: true }, ai: { online: true, status: "ready" },
  event: null, can_calibrate: true, can_start: true
};
const context = { authenticated: true, preview: false, serverOnline: true };
const copy = () => JSON.parse(JSON.stringify(factory));
assert.deepEqual(controls(factory, context), { calibrate: true, start: true, stop: true });
const firstCalibration = copy(); firstCalibration.motor.telemetry.calibrated = false; firstCalibration.motor.telemetry.area_clear = false;
assert.deepEqual(controls(firstCalibration, context), { calibrate: true, start: false, stop: true });
for (const status of ["awaiting_capture", "processing", "pending"]) {
  const f = copy(); f.event = { status };
  assert.deepEqual(controls(f, context), { calibrate: false, start: false, stop: true });
}
const offline = copy(); offline.motor.online = false;
assert.deepEqual(controls(offline, context), { calibrate: false, start: false, stop: true });
const noAI = copy(); noAI.ai.status = "error";
assert.deepEqual(controls(noAI, context), { calibrate: true, start: false, stop: true });
const invalidSensor = copy(); invalidSensor.motor.telemetry.sensor_valid = false;
assert.deepEqual(controls(invalidSensor, context), { calibrate: false, start: false, stop: true });
const moving = copy(); moving.motor.telemetry.motor_on = true;
assert.deepEqual(controls(moving, context), { calibrate: false, start: false, stop: true });
assert.deepEqual(controls(factory, { ...context, serverOnline: false }), { calibrate: false, start: false, stop: true });
assert.deepEqual(controls(factory, { ...context, commandBusy: true }), { calibrate: false, start: false, stop: true });
assert.deepEqual(controls(factory, { ...context, preview: true }), { calibrate: false, start: false, stop: false });
assert.deepEqual(controls(factory, { ...context, authenticated: false }), { calibrate: false, start: false, stop: false });
const backendBlocks = copy(); backendBlocks.can_start = false; backendBlocks.can_calibrate = false;
assert.deepEqual(controls(backendBlocks, context), { calibrate: false, start: false, stop: true });
assert.equal(eventLabel("recognized"), "Reconhecido");
assert.equal(commandLabel("pending"), "Solicitado — aguardando confirmação");
assert.equal(commandLabel("applied"), "Confirmado pela placa");
console.log("factory-ui: bloqueios e distinção entre pedido e confirmação verificados.");
