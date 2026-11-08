#include <Arduino.h>
#include "esp_arduino_version.h"

// Teste de bancada: ESP32 classico + TB6612FNG + HC-SR04 convencional.
// MOTOR: PWMA=25, AIN1=26, AIN2=27, STBY=33. VCC driver=3V3.
// SENSOR: TRIG=18; ECHO -> 2,2k -> D19 -> 3,3k -> GND; VCC sensor=5V.
// GND comum. Camera desconectada. Motor informado como 5V: usar VM adequado.
// NUNCA conectar ECHO de 5V diretamente ao ESP32.
// Nao e firmware de producao nem substitui emergencia fisica.
constexpr uint8_t PWM_PIN=25, IN1=26, IN2=27, STBY=33, TRIG=18, ECHO=19;
constexpr uint32_t SAMPLE_MS=65, ECHO_TIMEOUT_US=25000, BRAKE_MS=300;
constexpr uint32_t PAUSE_MS=5000;
bool waitingPiece=false;
uint32_t pauseStart=0;
constexpr float DROP_MM=20.0f, CLEAR_DROP_MM=10.0f, MAX_NOISE_MM=6.0f;
constexpr int SPEED_PERCENT=30, CAL_SAMPLES=32;
bool pwmReady=false, running=false, braking=false, calibrating=false, calibrated=false;
bool valid=false, areaClear=false;
uint32_t lastSample=0, lastValid=0, brakeStart=0, lastPrint=0;
float distanceMM=0, baseline=0, samples[CAL_SAMPLES];
int calCount=0, clearCount=0;

bool pwm(int value) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  return ledcWrite(PWM_PIN,value);
#else
  ledcWrite(0,value); return true;
#endif
}
void disableMotor() {
  digitalWrite(STBY,LOW);
  if(pwmReady) pwm(0);
  digitalWrite(IN1,LOW); digitalWrite(IN2,LOW);
  running=false; braking=false;
}
void stopMotor(const char *reason) {
  waitingPiece=false;
  if(running) {
    // IN1=IN2=HIGH com STBY=HIGH: short brake segundo tabela do TB6612.
    digitalWrite(IN1,HIGH); digitalWrite(IN2,HIGH);
    if(pwmReady) pwm(255);
    digitalWrite(STBY,HIGH);
    braking=true; brakeStart=millis();
  }
  running=false; areaClear=false; clearCount=0;
  Serial.print("PARADA: "); Serial.println(reason);
}
void help() {
  Serial.println("c = calibrar fundo com esteira VAZIA e motor parado (32 leituras)");
  Serial.println("g = iniciar, apenas apos calibracao e area livre");
  Serial.println("p = parar | s = estado | h = ajuda");
  Serial.println("Depois de g: peca -> pausa minima de 5 s -> retoma se area livre.");
  Serial.println("p ou falha cancela retomada automatica. Nao e aprovacao pela camera.");
}
void status() {
  if(valid) Serial.printf("Distancia: %.1f mm | ",distanceMM);
  else Serial.print("Distancia: INVALIDA | ");
  if(calibrated) Serial.printf("Fundo: %.1f | Parar <= %.1f | Livre >= %.1f mm | ",
                               baseline,baseline-DROP_MM,baseline-CLEAR_DROP_MM);
  if(running) Serial.println("COMANDO MOTOR ATIVO");
  else if(!pwmReady) Serial.println("PARADO | FALHA NA CONFIGURACAO PWM");
  else if(braking) Serial.println("PARADO | FRENAGEM EM ANDAMENTO");
  else if(waitingPiece) {
    uint32_t elapsed=millis()-pauseStart;
    if(elapsed<PAUSE_MS) Serial.printf("PAUSA DA PECA | faltam %.1f s\n",(PAUSE_MS-elapsed)/1000.0f);
    else Serial.println("PAUSA CONCLUIDA | aguardando area livre para retomar");
  }
  else if(calibrating) Serial.printf("PARADO | CALIBRANDO %d/%d\n",calCount,CAL_SAMPLES);
  else if(!calibrated) Serial.println("PARADO | FALTA CALIBRAR: esvazie a esteira e envie c");
  else if(!valid || millis()-lastValid>150) Serial.println("PARADO | SEM LEITURA VALIDA RECENTE");
  else if(!areaClear || distanceMM<baseline-CLEAR_DROP_MM)
    Serial.println("PARADO | AGUARDANDO AREA LIVRE / LEITURAS ESTAVEIS");
  else Serial.println("PARADO | PRONTO: envie g para iniciar");
}
void command(char c) {
  if(c=='p') { calibrating=false; stopMotor("operador"); }
  else if(c=='h') help();
  else if(c=='s') status();
  else if(c=='c') {
    if(running || braking) { Serial.println("Pare e aguarde antes de calibrar."); return; }
    waitingPiece=false; disableMotor(); calibrated=false; calibrating=true; calCount=0;
    areaClear=false; clearCount=0;
    Serial.println("Calibrando: mantenha esteira vazia e sensor fixo.");
  } else if(c=='g') {
    if(running) return;
    if(waitingPiece && millis()-pauseStart<PAUSE_MS) {
      Serial.println("Aguarde terminar a pausa minima de 5 segundos."); return;
    }
    if(!pwmReady || braking || calibrating || !calibrated || !valid || !areaClear ||
       millis()-lastValid>150 || distanceMM<baseline-CLEAR_DROP_MM) {
      Serial.println("Inicio bloqueado. Motivo abaixo:"); status(); return;
    }
    digitalWrite(STBY,LOW); digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);
    if(!pwm((SPEED_PERCENT*255+50)/100)) {
      waitingPiece=false; disableMotor(); Serial.println("Falha PWM: inicio bloqueado."); return;
    }
    waitingPiece=false; digitalWrite(STBY,HIGH); running=true;
    Serial.println("Motor acionado a 30% PWM. Deteccao: pausa de 5 s; falha: parada sem retomada.");
  } else if(c!='\r' && c!='\n' && c!=' ') {
    calibrating=false; stopMotor("comando desconhecido; use h");
  }
}
void measure() {
  // Leitura bloqueada no maximo por 25 ms; sem esperas longas ou medias em movimento.
  valid=false;
  if(digitalRead(ECHO)==LOW) {
    digitalWrite(TRIG,LOW); delayMicroseconds(2);
    digitalWrite(TRIG,HIGH); delayMicroseconds(10); digitalWrite(TRIG,LOW);
    unsigned long duration=pulseIn(ECHO,HIGH,ECHO_TIMEOUT_US);
    distanceMM=duration*0.343f/2.0f;
    valid=duration>0 && distanceMM>=20.0f && distanceMM<=4000.0f;
  }
  if(!valid) {
    areaClear=false; clearCount=0;
    if(calibrating) { calibrating=false; Serial.println("Calibracao abortada: leitura invalida."); }
    if(running || waitingPiece) stopMotor("sensor sem leitura valida; envie g depois de corrigir");
    return;
  }
  lastValid=millis();
  if(calibrating) {
    samples[calCount++]=distanceMM;
    if(calCount==CAL_SAMPLES) {
      // Ordenacao pequena, apenas com motor desabilitado.
      for(int i=1;i<CAL_SAMPLES;i++) {
        float value=samples[i]; int j=i-1;
        while(j>=0 && samples[j]>value) { samples[j+1]=samples[j]; --j; }
        samples[j+1]=value;
      }
      calibrating=false;
      baseline=(samples[15]+samples[16])/2.0f;
      if(samples[31]-samples[0]>MAX_NOISE_MM || baseline-DROP_MM<20.0f) {
        calibrated=false;
        Serial.println("Calibracao rejeitada: fundo instavel ou muito proximo. Ajuste montagem e repita c.");
      } else {
        calibrated=true;
        Serial.printf("Calibrado: fundo %.1f mm; deteccao <= %.1f mm.\n",baseline,baseline-DROP_MM);
      }
    }
    return;
  }
  if(!calibrated) return;
  if(distanceMM>baseline+20.0f) {
    areaClear=false; clearCount=0;
    if(running || waitingPiece) stopMotor("fundo fora da faixa calibrada; retomada cancelada");
  } else if(distanceMM<=baseline-DROP_MM) {
    areaClear=false; clearCount=0;
    if(running) {
      stopMotor("PECA DETECTADA: pausa minima de 5 segundos");
      waitingPiece=true; pauseStart=millis();
    }
  } else if(distanceMM>=baseline-CLEAR_DROP_MM) {
    if(clearCount<3) ++clearCount;
    if(clearCount>=3) areaClear=true;
  } else {
    clearCount=0; // Faixa de histerese: conservar areaClear anterior.
  }
}
void setup() {
  digitalWrite(STBY,LOW); pinMode(STBY,OUTPUT);
  digitalWrite(PWM_PIN,LOW); pinMode(PWM_PIN,OUTPUT);
  pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT); disableMotor();
  pinMode(TRIG,OUTPUT); digitalWrite(TRIG,LOW); pinMode(ECHO,INPUT);
  Serial.begin(115200);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  pwmReady=ledcAttach(PWM_PIN,20000,8);
#else
  pwmReady=ledcSetup(0,20000,8)>0;
  if(pwmReady) ledcAttachPin(PWM_PIN,0);
#endif
  disableMotor();
  delay(500);
  Serial.println("\nTESTE MOTOR 3 + ULTRASSONICO + PAUSA 5 S. Motor inicia desabilitado.");
  if(!pwmReady) Serial.println("ERRO PWM: motor bloqueado.");
  help();
}
void loop() {
  if(braking && millis()-brakeStart>=BRAKE_MS) disableMotor();
  if(Serial.available()) command((char)Serial.read());
  if(millis()-lastSample>=SAMPLE_MS) { lastSample=millis(); measure(); }
  if(waitingPiece && millis()-pauseStart>=PAUSE_MS && !braking && calibrated && valid &&
     areaClear && clearCount>=3 && millis()-lastValid<=150 &&
     distanceMM>=baseline-CLEAR_DROP_MM && distanceMM<=baseline+20.0f) command('g');
  if(millis()-lastPrint>=500) { lastPrint=millis(); status(); }
}
