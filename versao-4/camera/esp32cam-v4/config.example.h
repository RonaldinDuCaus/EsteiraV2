#pragma once

// Copie para config.h SOMENTE na sua maquina. Nao publique credenciais reais.
// A conta/token da camera e diferente da conta/token do motor.
constexpr char MF_WIFI_SSID[] = "PREENCHA_SUA_REDE";
constexpr char MF_WIFI_PASSWORD[] = "PREENCHA_SUA_SENHA";
constexpr char MF_SERVER_BASE_URL[] = "https://minifabrica.kronux.com.br"; // Sem / no final.
constexpr char MF_CAMERA_API_TOKEN[] = "PREENCHA_CAMERA_API_TOKEN";

// Core 3.3.12: usar bundle publico embutido com validacao da cadeia/hostname/relogio.
// Uma CA PEM customizada preenchida abaixo tem prioridade sobre o bundle.
#define MF_TLS_USE_BUILTIN_CA_BUNDLE true
// CA opcional para cadeia privada/customizada. Nao e chave privada nem token.
constexpr char MF_TLS_ROOT_CA[] = R"PEM(
)PEM";

// Apenas para bancada/rede de teste. Deixe false na VPS com HTTPS.
constexpr bool MF_ALLOW_HTTP_FOR_TESTS = false;
constexpr bool MF_CAMERA_USE_FLASH = false; // LED branco GPIO4; microSD nao usado.

constexpr unsigned long MF_POLL_INTERVAL_MS = 1000;
constexpr unsigned long MF_UPLOAD_RETRY_MS = 2000;
constexpr unsigned long MF_REQUEST_TIMEOUT_MS = 10000;
constexpr unsigned long MF_CONNECT_TIMEOUT_MS = 5000;
constexpr unsigned long MF_MAX_LEASE_SECONDS = 120;
constexpr size_t MF_MAX_JPEG_BYTES = 512 * 1024; // Limite defensivo para VGA JPEG.
