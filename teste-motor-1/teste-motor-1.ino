#include <Arduino.h>

// ESP32 classico. Teste automatico de UM motor DC de 5 V.
// IMPORTANTE: usar alimentacao REGULADA DE 5 V em VM, adequada a corrente do motor.
// NAO conectar o conjunto de baterias de 8,2 V diretamente a VM neste teste.
// VCC=3V3, GND comum, A1/A2=motor; BIN1/BIN2/PWMB=GND.
// Camera desconectada. Gravar com a alimentacao do motor desconectada.
// Este sketch inicia movimentos automaticamente, mesmo sem Monitor Serial.

constexpr uint8_t PWMA = 25;
constexpr uint8_t AIN1 = 26;
constexpr uint8_t AIN2 = 27;
constexpr uint8_t STBY = 33;
constexpr uint32_t INTERVALO_MS = 5000;

bool acionado = false;
uint32_t ultimaMudanca = 0;

void pararMotor() {
  digitalWrite(STBY, LOW); // Alta impedancia: motor para por inercia.
  digitalWrite(PWMA, LOW);
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
  acionado = false;
}

void ligarMotor() {
  digitalWrite(STBY, LOW);
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
  digitalWrite(PWMA, HIGH); // 100%: VM precisa estar adequado ao motor de 5 V.
  digitalWrite(STBY, HIGH);
  acionado = true;
}

void setup() {
  digitalWrite(STBY, LOW);
  pinMode(STBY, OUTPUT);
  digitalWrite(PWMA, LOW);
  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pararMotor();
  Serial.begin(115200);
  Serial.println("\nTeste automatico: 5 s ligado / 5 s desligado.");
  Serial.println("VM deve receber 5 V regulados. Primeiro acionamento em 5 s.");
  ultimaMudanca = millis();
}

void loop() {
  const uint32_t agora = millis();
  if (agora - ultimaMudanca >= INTERVALO_MS) {
    ultimaMudanca = agora;
    if (acionado) {
      pararMotor();
      Serial.println("DESLIGADO por 5 s (parada por inercia).");
    } else {
      ligarMotor();
      Serial.println("LIGADO por 5 s (comando enviado; sem sensor de rotacao).");
    }
  }
}
