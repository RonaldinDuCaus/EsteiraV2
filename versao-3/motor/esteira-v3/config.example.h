#pragma once
// Copie para config.h (ignorado pelo Git) e preencha localmente.
#define WIFI_SSID ""
#define WIFI_PASSWORD ""
#define SERVER_URL "https://seu-dominio.example"
#define MOTOR_API_TOKEN ""
// Cole a CA que valida o certificado da sua VPS. Nunca use setInsecure().
static const char SERVER_CA[] = R"CERT(
)CERT";
// Somente para bancada em rede confiavel. Nunca para a VPS publica.
#define ALLOW_LOCAL_HTTP false
constexpr int MOTOR_PWM_PERCENT = 100; // Motor informado como 5 V: VM regulado em 5 V.
