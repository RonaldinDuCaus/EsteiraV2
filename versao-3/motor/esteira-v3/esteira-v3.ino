#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_arduino_version.h>
#include <esp_system.h>
#include <time.h>
#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

// ESP32 classico; preserve o divisor 2,2k/3,3k no ECHO e GND comum.
constexpr uint8_t PWMA=25, IN1=26, IN2=27, STBY=33, TRIG=18, ECHO=19;
constexpr uint32_t PING_MS=65, ECHO_US=25000, BRAKE_MS=300, SETTLE_MS=500;
constexpr uint32_t LINK_TIMEOUT_MS=3000, ANALYSIS_MS=60000, EXIT_MS=3000;
constexpr int FREE_SAMPLES=8, CAL_SAMPLES=32;
constexpr float DROP_MM=20, CLEAR_DROP_MM=10, MAX_NOISE_MM=6;
enum class Mode { UNARMED, READY, CALIBRATING, MOVING, SETTLING, WAITING, EXITING, COMPLETING, REVIEW, FAULT };
Mode mode=Mode::UNARMED;
String bootId, eventId, completeId, terminalStatus, ackId, ackStatus, ackReason, calibrateId;
String lastStartId;
bool serverAuthorizationConfirmed=false;
bool requireFreshCommand=false;
uint32_t lastSafetyStopAt=0;
bool authorized=false, calibrated=false, sensorValid=false, areaClear=false, pwmReady=false;
bool outputOn=false, braking=false;
float distanceMM=0, baseline=0, samples[CAL_SAMPLES];
int freeCount=0, calCount=0;
uint32_t lastPing=0, brakeAt=0, detectedAt=0, exitAt=0, lastPrint=0;
uint32_t eventCounter=0;
SemaphoreHandle_t exchangeMutex;
struct Exchange {
  String telemetry, commandId, action, commandBoot, resultId, resultBoot, resultStatus, resultReason, completed, acknowledged;
  uint32_t contactAt=0, commandDeadline=0, commandIssuedAt=0;
  bool contacted=false, approved=false, serverAuthorized=false;
} exchange;

String uuid() {
  char value[37]; uint32_t a=esp_random(), b=esp_random(), c=esp_random(), d=esp_random();
  snprintf(value,sizeof(value),"%08lx-%04x-%04x-%04x-%04x%08lx",(unsigned long)a,
           (unsigned)(b>>16),(unsigned)((b&0x0fff)|0x4000),
           (unsigned)((c>>16&0x3fff)|0x8000),(unsigned)(c&0xffff),(unsigned long)d);
  return String(value);
}
const char* modeName() {
  switch(mode) {
    case Mode::READY:return "ready"; case Mode::CALIBRATING:return "calibrating";
    case Mode::MOVING:return "moving"; case Mode::SETTLING:return "settling";
    case Mode::WAITING:return "awaiting_analysis"; case Mode::EXITING:return "exiting";
    case Mode::COMPLETING:return "completing"; case Mode::REVIEW:return "review";
    case Mode::FAULT:return "fault"; default:return "disabled";
  }
}
bool pwm(int duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  return ledcWrite(PWMA,duty);
#else
  ledcWrite(0,duty); return true;
#endif
}
void standby() {
  digitalWrite(STBY,LOW); if(pwmReady) pwm(0);
  digitalWrite(IN1,LOW); digitalWrite(IN2,LOW); outputOn=false; braking=false;
}
void brake() {
  if(outputOn) {
    digitalWrite(IN1,HIGH); digitalWrite(IN2,HIGH); pwm(255); digitalWrite(STBY,HIGH);
    outputOn=false; braking=true; brakeAt=millis();
  }
}
void fault(const char* reason) {
  brake(); authorized=false;serverAuthorizationConfirmed=false; mode=Mode::FAULT;
  requireFreshCommand=true;lastSafetyStopAt=millis();
  if(calibrateId.length()) { ackId=calibrateId;ackStatus="rejected";ackReason=reason;calibrateId=""; }
  Serial.print("FALHA: "); Serial.println(reason);
}
bool drive() {
  if(!pwmReady) { fault("PWM indisponivel"); return false; }
  digitalWrite(STBY,LOW); digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);
  if(!pwm((MOTOR_PWM_PERCENT*255+50)/100)) { fault("Falha ao escrever PWM");return false; }
  digitalWrite(STBY,HIGH);outputOn=true;braking=false;return true;
}
bool terminal() { return terminalStatus=="unknown" || terminalStatus=="error" || terminalStatus=="cancelled"; }
bool canResetEvent() { return terminal() || (terminalStatus=="recognized" && !authorized); }
void acknowledge(const String& id, bool applied, const char* reason) {
  ackId=id;ackStatus=applied?"applied":"rejected";ackReason=reason;
}
void applyCommand(const Exchange& response) {
  if(!response.commandId.length() || response.commandId==ackId || response.commandId==calibrateId)return;
  const String id=response.commandId;
  if(response.commandBoot!=bootId) { acknowledge(id,false,"Inicializacao diferente");return; }
  if(response.action=="stop") {
    brake();authorized=false;serverAuthorizationConfirmed=false;mode=Mode::UNARMED;
    requireFreshCommand=true;lastSafetyStopAt=millis();
    if(calibrateId.length())calibrateId="";
    acknowledge(id,true,"Parada aplicada");return;
  }
  if((int32_t)(millis()-response.commandDeadline)>=0) { acknowledge(id,false,"Comando expirado");return; }
  if(requireFreshCommand && (int32_t)(response.commandIssuedAt-lastSafetyStopAt)<=0) {
    acknowledge(id,false,"Comando anterior a ultima parada/falha; solicite novamente");return;
  }
  if(response.action=="calibrate") {
    if(outputOn || braking || mode==Mode::WAITING || mode==Mode::SETTLING || mode==Mode::COMPLETING ||
       (eventId.length() && !canResetEvent()) || !sensorValid ||
       (eventId.length() && (!areaClear || freeCount<FREE_SAMPLES))) {
      acknowledge(id,false,"Pare, remova a peca e aguarde finalizar o evento");return;
    }
    authorized=false;serverAuthorizationConfirmed=false;standby();calibrated=false;calCount=0;freeCount=0;areaClear=false;
    if(eventId.length()) { completeId=eventId;eventId="";terminalStatus=""; }
    mode=Mode::CALIBRATING;calibrateId=id;return;
  }
  if(response.action=="start") {
    if(!calibrated || !sensorValid || !areaClear || freeCount<FREE_SAMPLES || braking ||
       eventId.length() || completeId.length() || mode==Mode::CALIBRATING) {
      acknowledge(id,false,"Calibracao/area livre/evento pendente");return;
    }
    authorized=true;
    if(drive()) {requireFreshCommand=false;lastStartId=id;serverAuthorizationConfirmed=false;mode=Mode::MOVING;acknowledge(id,true,"Partida aplicada");}
    else acknowledge(id,false,"Falha no acionamento");
    return;
  }
  acknowledge(id,false,"Comando desconhecido");
}
void measure() {
  sensorValid=false;
  if(digitalRead(ECHO)==LOW) {
    digitalWrite(TRIG,LOW);delayMicroseconds(2);digitalWrite(TRIG,HIGH);delayMicroseconds(10);digitalWrite(TRIG,LOW);
    unsigned long duration=pulseIn(ECHO,HIGH,ECHO_US);
    distanceMM=duration*0.343f/2;
    sensorValid=duration>0 && distanceMM>=20 && distanceMM<=4000;
  }
  if(!sensorValid || (calibrated && distanceMM>baseline+20)) {
    areaClear=false;freeCount=0;
    if(authorized || mode==Mode::CALIBRATING)fault("Sensor invalido ou fundo fora da faixa");
    return;
  }
  if(mode==Mode::CALIBRATING) {
    samples[calCount++]=distanceMM;
    if(calCount==CAL_SAMPLES) {
      for(int i=1;i<CAL_SAMPLES;i++){float value=samples[i];int j=i-1;while(j>=0&&samples[j]>value){samples[j+1]=samples[j];--j;}samples[j+1]=value;}
      baseline=(samples[15]+samples[16])/2;
      if(samples[31]-samples[0]>MAX_NOISE_MM || baseline-DROP_MM<20)fault("Calibracao instavel ou fundo proximo");
      else {calibrated=true;mode=Mode::READY;acknowledge(calibrateId,true,"Calibracao concluida");calibrateId="";}
    }
    return;
  }
  if(!calibrated)return;
  if(distanceMM>=baseline-CLEAR_DROP_MM) {if(freeCount<FREE_SAMPLES)++freeCount;areaClear=freeCount>=FREE_SAMPLES;}
  else {freeCount=0;areaClear=false;}
  if(mode==Mode::MOVING && distanceMM<=baseline-DROP_MM) {
    brake();detectedAt=millis();terminalStatus="";mode=Mode::SETTLING;
    // O evento so vai para a rede depois da estabilizacao mecanica.
    eventId=bootId+"-"+String(++eventCounter);
  }
  if(mode==Mode::EXITING && areaClear) {
    standby();completeId=eventId;mode=Mode::COMPLETING;
  }
}
// UTC do servidor, usado apenas para TTL conservador do comando recebido.
int64_t isoMillis(const char* text) {
  int y,M,d,h,m,s;if(sscanf(text,"%d-%d-%dT%d:%d:%d",&y,&M,&d,&h,&m,&s)!=6)return 0;
  tm t={};t.tm_year=y-1900;t.tm_mon=M-1;t.tm_mday=d;t.tm_hour=h;t.tm_min=m;t.tm_sec=s;t.tm_isdst=0;
  int fraction=0;
  if(strlen(text)>19 && text[19]=='.') {
    int scale=100;for(int i=20;scale>0 && text[i]>='0'&&text[i]<='9';++i,scale/=10)fraction+=(text[i]-'0')*scale;
  }
  return (int64_t)mktime(&t)*1000+fraction;
}
bool configReady() {
  return strlen(WIFI_SSID)>0 && strlen(MOTOR_API_TOKEN)>=16 &&
    ((String(SERVER_URL).startsWith("https://") && strlen(SERVER_CA)>32) ||
     (ALLOW_LOCAL_HTTP && String(SERVER_URL).startsWith("http://")));
}
void networkTask(void*) {
  WiFi.mode(WIFI_STA);WiFi.setAutoReconnect(true);
  if(!configReady()) {Serial.println("Configure config.h: Wi-Fi, URL, token e CA. Motor bloqueado.");vTaskDelete(nullptr);return;}
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);configTime(0,0,"pool.ntp.org","time.google.com");
  uint32_t retryAt=0;
  for(;;) {
    if(WiFi.status()!=WL_CONNECTED) {
      if(millis()-retryAt>10000){retryAt=millis();WiFi.reconnect();}
      vTaskDelay(pdMS_TO_TICKS(200));continue;
    }
    bool https=String(SERVER_URL).startsWith("https://");
    if(https && time(nullptr)<1700000000){vTaskDelay(pdMS_TO_TICKS(300));continue;}
    String body;
    xSemaphoreTake(exchangeMutex,portMAX_DELAY);body=exchange.telemetry;xSemaphoreGive(exchangeMutex);
    if(!body.length()){vTaskDelay(pdMS_TO_TICKS(100));continue;}
    WiFiClient plain;WiFiClientSecure secure;HTTPClient http;
    if(https)secure.setCACert(SERVER_CA);
    String url=String(SERVER_URL)+"/api/v1/devices/motor/sync";
    bool began=https?http.begin(secure,url):http.begin(plain,url);
    if(began) {
      http.setConnectTimeout(1500);http.setTimeout(1500);
      http.addHeader("Authorization",String("Bearer ")+MOTOR_API_TOKEN);http.addHeader("Content-Type","application/json");
      uint32_t requestedAt=millis();int code=http.POST(body);
      if(code==200 && http.getSize()<=16384) {
        JsonDocument json;
        if(!deserializeJson(json,http.getStream()) && String(json["boot_id"]|"")==bootId) {
          Exchange next;
          next.contacted=true;next.contactAt=millis();
          next.commandId=json["command"]["id"]|"";next.action=json["command"]["action"]|"";
          next.commandBoot=json["command"]["boot_id"]|"";
          int64_t expires=isoMillis(json["command"]["expires_at"]|"");int64_t now=isoMillis(json["server_time"]|"");
          int64_t created=isoMillis(json["command"]["created_at"]|"");
          int64_t ttl=(expires>now && now>0)?expires-now:0;if(ttl>30000)ttl=0;
          next.commandDeadline=requestedAt+(uint32_t)ttl;
          // A estimativa e conservadora: desconta tambem o tempo de rede da partida.
          next.commandIssuedAt=(now>=created && created>0 && now-created<60000)?requestedAt-(uint32_t)(now-created):0;
          next.resultId=json["event"]["event_id"]|"";next.resultBoot=json["event"]["boot_id"]|"";
          next.resultStatus=json["event"]["status"]|"";next.resultReason=json["event"]["reason"]|"";
          next.approved=json["event"]["approved"]|false;next.completed=json["completed_event_id"]|"";
          next.serverAuthorized=json["authorized"]|false;next.acknowledged=json["acknowledged_command_id"]|"";
          xSemaphoreTake(exchangeMutex,portMAX_DELAY);
          String keep=exchange.telemetry;exchange=next;exchange.telemetry=keep;
          xSemaphoreGive(exchangeMutex);
        }
      }
      http.end();
    }
    vTaskDelay(pdMS_TO_TICKS(300));
  }
}
void publishTelemetry() {
  JsonDocument j;j["boot_id"]=bootId;j["state"]=modeName();j["motor_on"]=outputOn;
  j["firmware_version"]="esteira-v3.0";
  j["calibrated"]=calibrated;j["sensor_valid"]=sensorValid;j["area_clear"]=areaClear;
  if(calibrated)j["baseline_mm"]=baseline;else j["baseline_mm"]=nullptr;
  if(sensorValid)j["distance_mm"]=distanceMM;else j["distance_mm"]=nullptr;
  if(eventId.length() && mode!=Mode::SETTLING)j["event_id"]=eventId;else j["event_id"]=nullptr;
  if(completeId.length())j["completed_event_id"]=completeId;else j["completed_event_id"]=nullptr;
  if(ackId.length()){j["ack_command_id"]=ackId;j["ack_status"]=ackStatus;j["ack_reason"]=ackReason;}
  String body;serializeJson(j,body);
  xSemaphoreTake(exchangeMutex,portMAX_DELAY);exchange.telemetry=body;xSemaphoreGive(exchangeMutex);
}
void setup() {
  digitalWrite(STBY,LOW);pinMode(STBY,OUTPUT);digitalWrite(PWMA,LOW);pinMode(PWMA,OUTPUT);
  pinMode(IN1,OUTPUT);pinMode(IN2,OUTPUT);standby();
  pinMode(TRIG,OUTPUT);digitalWrite(TRIG,LOW);pinMode(ECHO,INPUT);Serial.begin(115200);
  setenv("TZ","UTC0",1);tzset();bootId=uuid();
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  pwmReady=ledcAttach(PWMA,20000,8);
#else
  pwmReady=ledcSetup(0,20000,8)>0;if(pwmReady)ledcAttachPin(PWMA,0);
#endif
  standby();exchangeMutex=xSemaphoreCreateMutex();
  if(!exchangeMutex){mode=Mode::FAULT;Serial.println("Sem memoria para comunicacao");return;}
  publishTelemetry();
  if(xTaskCreatePinnedToCore(networkTask,"server",12288,nullptr,1,nullptr,0)!=pdPASS){mode=Mode::FAULT;return;}
  Serial.println("Esteira V3: desabilitada. Use Calibrar/Iniciar/Parar na dashboard. Serial p para parar localmente.");
}
void loop() {
  if(!exchangeMutex){standby();delay(10);return;}
  if(braking && millis()-brakeAt>=BRAKE_MS)standby();
  Exchange response;
  xSemaphoreTake(exchangeMutex,portMAX_DELAY);response=exchange;xSemaphoreGive(exchangeMutex);
  bool linked=response.contacted && millis()-response.contactAt<LINK_TIMEOUT_MS;
  if(!linked && (authorized || mode==Mode::CALIBRATING))fault("Comunicacao expirada; nova autorizacao necessaria");
  if(Serial.available()) {
    char c=Serial.read();if(c=='p'){brake();authorized=false;serverAuthorizationConfirmed=false;requireFreshCommand=true;lastSafetyStopAt=millis();mode=Mode::UNARMED;Serial.println("Parada local aplicada");}
  }
  if(millis()-lastPing>=PING_MS){lastPing=millis();measure();}
  if(linked)applyCommand(response);
  if(authorized && linked) {
    if(response.serverAuthorized)serverAuthorizationConfirmed=true;
    else if(serverAuthorizationConfirmed || (lastStartId.length() && response.acknowledged==lastStartId))
      fault("Servidor revogou/recusou a autorizacao; nova partida necessaria");
  }
  if(mode==Mode::SETTLING && millis()-detectedAt>=SETTLE_MS)mode=Mode::WAITING;
  if(mode==Mode::WAITING) {
    if(millis()-detectedAt>ANALYSIS_MS)fault("Analise excedeu prazo; motor permanece parado");
    else if(linked && response.resultId==eventId && response.resultBoot==bootId) {
      terminalStatus=response.resultStatus;
      if(response.approved && terminalStatus=="recognized" && authorized && sensorValid && !braking) {
        freeCount=0;areaClear=false;exitAt=millis();if(drive())mode=Mode::EXITING;
      } else if(terminal()){mode=Mode::REVIEW;Serial.print("Conferencia: ");Serial.println(response.resultReason);}
    }
  }
  if(mode==Mode::EXITING && millis()-exitAt>EXIT_MS)fault("Peca nao saiu no prazo de 3 s");
  if(completeId.length() && linked && response.completed==completeId) {
    completeId="";eventId="";terminalStatus="";
    if(mode==Mode::COMPLETING) {mode=Mode::READY;if(authorized && sensorValid && areaClear && drive())mode=Mode::MOVING;}
  }
  // Resultados terminais tambem precisam ser visiveis apos uma parada/falha.
  if(linked && eventId.length() && response.resultId==eventId && response.resultBoot==bootId &&
     (mode==Mode::UNARMED || mode==Mode::FAULT))terminalStatus=response.resultStatus;
  publishTelemetry();
  if(millis()-lastPrint>=1000){lastPrint=millis();Serial.printf("Estado %s | distancia %.1f mm | saida %s | servidor %s\n",modeName(),distanceMM,outputOn?"acionada":"parada",linked?"recente":"sem contato");}
  delay(2);
}
