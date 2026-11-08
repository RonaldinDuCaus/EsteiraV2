#pragma once
// Copie para config.h (ignorado pelo Git) e preencha localmente.
#define WIFI_SSID ""
#define WIFI_PASSWORD ""
#define SERVER_URL "https://minifabrica.kronux.com.br"
#define MOTOR_API_TOKEN ""
// Core 3.3.12: bundle publico embutido, com validacao da cadeia/hostname/relogio.
// Se preencher SERVER_CA com uma CA PEM customizada, ela tem prioridade.
#define TLS_USE_BUILTIN_CA_BUNDLE true
// Opcional: cole a CA que valida uma cadeia privada/customizada. Nunca setInsecure().
static const char SERVER_CA[] = R"CERT(
)CERT";
// Somente para bancada em rede confiavel. Nunca para a VPS publica.
#define ALLOW_LOCAL_HTTP false
constexpr int MOTOR_PWM_PERCENT = 100; // Motor informado como 5 V: VM regulado em 5 V.
