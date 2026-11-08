#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <ctype.h>
#include "esp_camera.h"
#include "esp_system.h"

#if __has_include("config.h")
#include "config.h"
#else
#error "Copie config.example.h para config.h e configure rede, servidor, token e CA."
#endif

// ESP32-CAM AI Thinker + OV2640 + PSRAM. Nao usar esta pinagem em outra placa.
// Pinos internos da camera conforme exemplo oficial Arduino-ESP32 da Espressif.
constexpr char FIRMWARE_VERSION[] = "minifabrica-camera-v3.0.0";
constexpr uint8_t FLASH_PIN = 4;
constexpr size_t MAX_REPLY_BYTES = 8192;
constexpr time_t MIN_VALID_TIME = 1735689600; // 2025-01-01 UTC.

String bootId;
String serverBase;
String cameraError;
bool configReady = false;
bool cameraReady = false;
bool authFault = false;
bool httpsServer = true;
unsigned long lastPoll = 0;
unsigned long lastUploadTry = 0;
unsigned long lastWiFiTry = 0;
unsigned long lastCameraTry = 0;
unsigned long lastClockNotice = 0;

struct PendingCapture {
  String id;
  String eventId;
  String motorBootId;
  String leaseToken;
  String failureReason;
  time_t expiresAtUtc = 0;
  unsigned long receivedAtMs = 0;
  unsigned long validForMs = 0;
  camera_fb_t *frame = nullptr;
  bool active = false;
} pending;

// Limita a resposta antes de acumular seu corpo em RAM; nao imprime tokens/corpo.
class BoundedReply : public Stream {
 public:
  String body;
  bool overflow = false;
  int available() override { return 0; }
  int read() override { return -1; }
  int peek() override { return -1; }
  void flush() override {}
  size_t write(uint8_t value) override { return write(&value, 1); }
  size_t write(const uint8_t *buffer, size_t length) override {
    if (length > MAX_REPLY_BYTES - body.length()) { overflow = true; return 0; }
    if (!body.concat(reinterpret_cast<const char *>(buffer), length)) return 0;
    return length;
  }
};

String makeBootId() {
  uint8_t bytes[16];
  esp_fill_random(bytes, sizeof(bytes));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  char value[37];
  snprintf(value, sizeof(value),
           "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
           bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7],
           bytes[8], bytes[9], bytes[10], bytes[11], bytes[12], bytes[13], bytes[14], bytes[15]);
  return String(value);
}

bool isIdentifier(const String &value) {
  if (value.length() < 1 || value.length() > 80) return false;
  for (size_t i = 0; i < value.length(); ++i) {
    unsigned char c = value[i];
    if (!isalnum(c) && c != '-' && c != '_') return false;
  }
  return true;
}

time_t parseUtc(const String &value) {
  if (value.length() < 20) return 0;
  int year, month, day, hour, minute, second;
  if (sscanf(value.c_str(), "%d-%d-%dT%d:%d:%d", &year, &month, &day,
             &hour, &minute, &second) != 6) return 0;
  if (year < 2025 || month < 1 || month > 12 || day < 1 || day > 31 ||
      hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) return 0;
  size_t pos = 19;
  if (pos < value.length() && value[pos] == '.') {
    ++pos;
    while (pos < value.length() && isdigit(static_cast<unsigned char>(value[pos]))) ++pos;
  }
  const String zone = value.substring(pos);
  if (zone != "Z" && zone != "+00:00" && zone != "+0000") return 0;
  struct tm parsed = {};
  parsed.tm_year = year - 1900; parsed.tm_mon = month - 1; parsed.tm_mday = day;
  parsed.tm_hour = hour; parsed.tm_min = minute; parsed.tm_sec = second;
  parsed.tm_isdst = 0;
  return mktime(&parsed); // TZ=UTC0 definido em setup().
}

bool clockReady() { return time(nullptr) >= MIN_VALID_TIME; }

bool validConfiguration() {
  serverBase = String(MF_SERVER_BASE_URL);
  while (serverBase.endsWith("/")) serverBase.remove(serverBase.length() - 1);
  httpsServer = serverBase.startsWith("https://");
  if (!httpsServer && !(MF_ALLOW_HTTP_FOR_TESTS && serverBase.startsWith("http://"))) {
    cameraError = "Servidor exige HTTPS; HTTP so e permitido com opt-in de bancada."; return false;
  }
  if (serverBase.indexOf("SEU-DOMINIO") >= 0 || serverBase.indexOf('?') >= 0 ||
      serverBase.indexOf('#') >= 0 || serverBase.indexOf('@') >= 0 ||
      String(MF_WIFI_SSID).startsWith("PREENCHA") ||
      String(MF_CAMERA_API_TOKEN).startsWith("PREENCHA") || strlen(MF_CAMERA_API_TOKEN) < 16) {
    cameraError = "Preencha config.h com rede, servidor e token exclusivo da camera."; return false;
  }
  if (httpsServer && String(MF_TLS_ROOT_CA).indexOf("-----BEGIN CERTIFICATE-----") < 0) {
    cameraError = "CA do servidor HTTPS ausente em config.h."; return false;
  }
  return true;
}

// Um cliente por requisicao, sem redirecionamentos e sem setInsecure().
// No modo HTTPS, a CA e o relogio validam o certificado do servidor.
int postBytes(const String &path, const uint8_t *bytes, size_t length,
              const char *contentType, String &reply, bool withLease) {
  reply = "";
  if (!configReady || authFault || WiFi.status() != WL_CONNECTED ||
      (httpsServer && !clockReady())) return -1000;
  WiFiClient plain;
  WiFiClientSecure secure;
  HTTPClient http;
  bool opened;
  if (httpsServer) {
    secure.setCACert(MF_TLS_ROOT_CA);
    secure.setHandshakeTimeout(10);
    opened = http.begin(secure, serverBase + path);
  } else {
    opened = http.begin(plain, serverBase + path);
  }
  if (!opened) return -1001;
  http.setConnectTimeout(MF_CONNECT_TIMEOUT_MS);
  http.setTimeout(MF_REQUEST_TIMEOUT_MS);
  http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
  http.addHeader("Authorization", String("Bearer ") + MF_CAMERA_API_TOKEN);
  http.addHeader("Content-Type", contentType);
  if (withLease) {
    http.addHeader("X-Capture-Lease", pending.leaseToken);
    http.addHeader("X-Camera-Boot-ID", bootId);
  }
  int result = http.POST(const_cast<uint8_t *>(bytes), length);
  if (result > 0) {
    BoundedReply response;
    int copied = http.writeToStream(&response);
    if (response.overflow || copied < 0) result = -1002;
    else reply = response.body;
  }
  http.end();
  if (result == 401 || result == 403) {
    authFault = true;
    Serial.println("Autenticacao da camera recusada. Confira CAMERA_API_TOKEN e reinicie.");
  }
  return result;
}

int postJson(const String &path, const JsonDocument &document, String &reply) {
  String body;
  serializeJson(document, body);
  return postBytes(path, reinterpret_cast<const uint8_t *>(body.c_str()), body.length(),
                   "application/json", reply, false);
}

void releasePending() {
  digitalWrite(FLASH_PIN, LOW);
  if (pending.frame) esp_camera_fb_return(pending.frame);
  pending = PendingCapture();
}

bool leaseExpired() {
  if (!pending.active) return false;
  if (millis() - pending.receivedAtMs >= pending.validForMs) return true;
  return clockReady() && time(nullptr) >= pending.expiresAtUtc;
}

bool initializeCamera() {
  digitalWrite(FLASH_PIN, LOW);
  if (!psramFound()) { cameraError = "PSRAM nao detectada; captura bloqueada."; return false; }
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 5; config.pin_d1 = 18; config.pin_d2 = 19; config.pin_d3 = 21;
  config.pin_d4 = 36; config.pin_d5 = 39; config.pin_d6 = 34; config.pin_d7 = 35;
  config.pin_xclk = 0; config.pin_pclk = 22; config.pin_vsync = 25; config.pin_href = 23;
  config.pin_sccb_sda = 26; config.pin_sccb_scl = 27;
  config.pin_pwdn = 32; config.pin_reset = -1;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  esp_err_t error = esp_camera_init(&config);
  if (error != ESP_OK) {
    cameraError = String("Falha de inicializacao: ") + esp_err_to_name(error);
    esp_camera_deinit();
    return false;
  }
  sensor_t *sensor = esp_camera_sensor_get();
  if (!sensor || sensor->id.PID != OV2640_PID) {
    cameraError = "Sensor diferente de OV2640; conferir placa/pinagem.";
    esp_camera_deinit();
    return false;
  }
  cameraError = "";
  Serial.println("Camera pronta: AI Thinker / OV2640 / JPEG 640x480 / PSRAM.");
  return true;
}

void captureCurrentJob() {
  if (!pending.active || pending.frame || pending.failureReason.length()) return;
  if (!cameraReady || leaseExpired()) { pending.failureReason = "camera_not_ready_or_lease_expired"; return; }
  if (MF_CAMERA_USE_FLASH) { digitalWrite(FLASH_PIN, HIGH); delay(80); }
  camera_fb_t *oldFrame = esp_camera_fb_get();
  if (oldFrame) esp_camera_fb_return(oldFrame); // Primeiro quadro pode estar na fila.
  camera_fb_t *frame = esp_camera_fb_get();
  digitalWrite(FLASH_PIN, LOW); // Inclusive falha de captura.
  if (!frame) {
    pending.failureReason = "capture_failed";
    cameraError = "Falha ao obter quadro.";
    return;
  }
  if (frame->format != PIXFORMAT_JPEG || frame->len < 4 || frame->len > MF_MAX_JPEG_BYTES ||
      frame->buf[0] != 0xff || frame->buf[1] != 0xd8 ||
      frame->buf[frame->len - 2] != 0xff || frame->buf[frame->len - 1] != 0xd9) {
    esp_camera_fb_return(frame);
    pending.failureReason = "invalid_jpeg_frame";
    cameraError = "Quadro JPEG invalido.";
    return;
  }
  pending.frame = frame; // Guardar EXATAMENTE estes bytes para qualquer reenvio.
  Serial.printf("Foto vinculada ao evento %s: %u bytes.\n", pending.eventId.c_str(),
                static_cast<unsigned>(frame->len));
}

void retryPending() {
  if (!pending.active) return;
  if (leaseExpired()) {
    Serial.println("Reserva de captura expirou; foto descartada sem reutilizar em outro evento.");
    releasePending(); return;
  }
  if (millis() - lastUploadTry < MF_UPLOAD_RETRY_MS) return;
  lastUploadTry = millis();
  if (WiFi.status() != WL_CONNECTED || (httpsServer && !clockReady()) || authFault) return;
  captureCurrentJob();
  if (leaseExpired()) {
    Serial.println("Reserva terminou durante a captura; nao enviar fotografia vencida.");
    releasePending(); return;
  }
  String reply;
  int status;
  if (pending.failureReason.length()) {
    JsonDocument failure;
    failure["boot_id"] = bootId;
    failure["lease_token"] = pending.leaseToken;
    failure["reason"] = pending.failureReason;
    status = postJson("/api/v1/devices/camera/captures/" + pending.id + "/failure", failure, reply);
  } else if (pending.frame) {
    status = postBytes("/api/v1/devices/camera/captures/" + pending.id,
                       pending.frame->buf, pending.frame->len, "image/jpeg", reply, true);
  } else {
    return;
  }
  if (status >= 200 && status < 300) {
    JsonDocument ack;
    const bool badJson = static_cast<bool>(deserializeJson(ack, reply));
    const bool matchingAck = !badJson && (pending.failureReason.length()
      ? (ack["ok"].is<bool>() && ack["ok"].as<bool>())
      : String(ack["event_id"] | "") == pending.eventId);
    if (!matchingAck) {
      Serial.println("Resposta 2xx sem confirmacao do pedido correto; manter a mesma foto/reserva.");
      return;
    }
    Serial.println(pending.failureReason.length() ? "Falha da captura registrada no servidor."
                                                : "Upload confirmado pelo servidor para esta captura.");
    cameraError = pending.failureReason.length() ? pending.failureReason : "";
    releasePending();
  } else if ((status == 413 || status == 415 || status == 422) && !pending.failureReason.length()) {
    if (pending.frame) { esp_camera_fb_return(pending.frame); pending.frame = nullptr; }
    pending.failureReason = String("upload_rejected_http_") + status;
    Serial.printf("Imagem recusada (HTTP %d); registrar falha do mesmo pedido.\n", status);
  } else if (status == 404 || status == 409 || status == 410 || status == 413 || status == 415 || status == 422) {
    Serial.printf("Captura recusada/encerrada (HTTP %d); nao reutilizar esta foto.\n", status);
    releasePending();
  } else {
    Serial.printf("Upload/falha sem confirmacao (%d); manter mesmo pedido e bytes ate expirar.\n", status);
  }
}

void pollServer() {
  JsonDocument request;
  request["boot_id"] = bootId;
  request["ready"] = cameraReady;
  request["firmware_version"] = FIRMWARE_VERSION;
  if (cameraError.length()) request["error"] = cameraError;
  String reply;
  const int status = postJson("/api/v1/devices/camera/poll", request, reply);
  if (status < 200 || status >= 300) {
    Serial.printf("Consulta da camera sem confirmacao (%d).\n", status); return;
  }
  JsonDocument response;
  if (deserializeJson(response, reply)) { Serial.println("Resposta de consulta invalida."); return; }
  JsonVariant job = response["capture"];
  if (job.isNull()) return;
  if (!cameraReady) { Serial.println("Pedido ignorado: camera nao esta pronta."); return; }
  String captureId = job["id"] | "";
  String eventId = job["event_id"] | "";
  String motorBootId = job["motor_boot_id"] | "";
  String leaseToken = job["lease_token"] | "";
  time_t expiry = parseUtc(String(job["expires_at"] | ""));
  time_t serverTime = parseUtc(String(response["server_time"] | ""));
  const long ttl = static_cast<long>(expiry - serverTime);
  if (!isIdentifier(captureId) || !isIdentifier(eventId) || !isIdentifier(motorBootId) ||
      leaseToken.length() < 16 || leaseToken.length() > 256 || serverTime < MIN_VALID_TIME ||
      ttl <= 0 || static_cast<unsigned long>(ttl) > MF_MAX_LEASE_SECONDS ||
      (clockReady() && time(nullptr) >= expiry)) {
    Serial.println("Pedido com IDs/reserva/validade invalidos: captura bloqueada."); return;
  }
  pending.id = captureId;
  pending.eventId = eventId;
  pending.motorBootId = motorBootId;
  pending.leaseToken = leaseToken;
  pending.expiresAtUtc = expiry;
  pending.receivedAtMs = millis();
  pending.validForMs = static_cast<unsigned long>(ttl) * 1000UL;
  pending.active = true;
  lastUploadTry = millis() - MF_UPLOAD_RETRY_MS;
  Serial.printf("Pedido recebido para evento %s.\n", eventId.c_str());
}

void setup() {
  pinMode(FLASH_PIN, OUTPUT);
  digitalWrite(FLASH_PIN, LOW);
  Serial.begin(115200);
  delay(500);
  setenv("TZ", "UTC0", 1); tzset();
  bootId = makeBootId();
  Serial.printf("\n%s | boot %s\n", FIRMWARE_VERSION, bootId.c_str());
  configReady = validConfiguration();
  if (!configReady) { Serial.println(cameraError); return; }
  cameraReady = initializeCamera();
  if (!cameraReady) Serial.println(cameraError);
  lastCameraTry = millis();
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(MF_WIFI_SSID, MF_WIFI_PASSWORD);
  lastWiFiTry = millis();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("Conectando Wi-Fi. Conexao de rede nao significa camera pronta.");
}

void loop() {
  digitalWrite(FLASH_PIN, LOW);
  if (!configReady) { delay(100); return; }
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWiFiTry >= 10000) {
      lastWiFiTry = millis(); WiFi.reconnect();
      Serial.println("Wi-Fi indisponivel; tentando reconectar.");
    }
  } else if (httpsServer && !clockReady()) {
    if (millis() - lastClockNotice >= 10000) {
      lastClockNotice = millis();
      Serial.println("Aguardando relogio NTP para validar HTTPS. Nao sera usado TLS inseguro.");
    }
  }
  if (pending.active) {
    retryPending(); // Nunca reservar outro evento enquanto ainda possui a foto deste.
  } else {
    if (!cameraReady && millis() - lastCameraTry >= 10000) {
      lastCameraTry = millis(); cameraReady = initializeCamera();
    }
    if (!authFault && WiFi.status() == WL_CONNECTED && (!httpsServer || clockReady()) &&
        millis() - lastPoll >= MF_POLL_INTERVAL_MS) {
      lastPoll = millis(); pollServer();
    }
  }
  delay(5);
}
