# ESP32-CAM — Versão 3

Firmware para a **ESP32-CAM AI Thinker com OV2640 e PSRAM**, modelo confirmado pelo usuário. Esta placa captura e envia fotos; o processamento YOLOv8 ocorre no servidor. Não há classificação de imagens na placa, microSD ou persistência local de fotos nesta versão.

Arquivo: [esp32cam-v3.ino](esp32cam-v3/esp32cam-v3.ino). Configuração de exemplo: [config.example.h](esp32cam-v3/config.example.h).

## Configurar e gravar

1. Instalar Arduino IDE e o pacote **esp32 by Espressif Systems 3.x**. Instalar a biblioteca **ArduinoJson 7.x** pelo gerenciador de bibliotecas. O driver `esp_camera.h` acompanha o pacote ESP32.
2. Copiar `esp32cam-v3/config.example.h` para `esp32cam-v3/config.h` na máquina de gravação. O arquivo local `config.h` contém segredos e deve permanecer ignorado pelo Git.
3. Preencher `MF_WIFI_SSID`, `MF_WIFI_PASSWORD`, `MF_SERVER_BASE_URL` e `MF_CAMERA_API_TOKEN`. O token deve corresponder a `CAMERA_API_TOKEN` no servidor, e ser diferente do token da placa do motor. O endereço base inclui `https://` e não deve conter usuário/senha, query ou fragmento.
4. Preencher `MF_TLS_ROOT_CA` com o certificado CA em PEM que valida o certificado do domínio da VPS/proxy. Não inserir uma chave privada. O firmware valida o certificado e aguarda sincronização NTP; nunca usa `setInsecure()`.
5. Selecionar **AI Thinker ESP32-CAM**, porta correta e PSRAM habilitada quando a opção estiver disponível. Usar alimentação estável apropriada à placa. O GPIO0 é ligado ao GND somente para entrar no modo de gravação; retirar essa ligação e reiniciar para executar. Os sinais do adaptador serial devem ser de 3,3 V. Não ligar a bateria de motor de 8–8,4 V à câmera.
6. Abrir Monitor Serial em **115200 baud**. Confirmar `Camera pronta: AI Thinker / OV2640 / JPEG 640x480 / PSRAM`. Rede conectada e câmera pronta são estados distintos.

Para um teste de rede isolado por HTTP, usar endereço `http://...` e habilitar explicitamente `MF_ALLOW_HTTP_FOR_TESTS=true`. Essa opção não é para a VPS definitiva nem protege o token durante o transporte. Não é preciso abrir portas de entrada na rede da câmera: ela inicia todas as conexões com o servidor.

## Captura e vínculo com a peça

1. A câmera inicializa, verifica PSRAM e OV2640 e gera um `boot_id` UUID exclusivo desta inicialização.
2. Consulta `POST /api/v1/devices/camera/poll` com Bearer próprio e JSON `{boot_id, ready, firmware_version, error?}`. Somente `ready=true` pode reservar um pedido.
3. O servidor devolve `capture` com `id`, `event_id`, `motor_boot_id`, `lease_token` e `expires_at`, ou `null`. `server_time` e validade vêm em UTC.
4. O firmware descarta o primeiro quadro possivelmente antigo e captura um JPEG VGA de 640 × 480, qualidade 12 e um framebuffer em PSRAM. Se habilitado, o flash GPIO4 acende apenas na captura e é desligado em falhas e no restante do programa. O microSD não é utilizado.
5. Envia o mesmo JPEG como corpo binário a `POST /api/v1/devices/camera/captures/{id}`. Cabeçalhos: `Authorization: Bearer ...`, `Content-Type: image/jpeg`, `X-Capture-Lease` e `X-Camera-Boot-ID`.
6. Uma resposta 2xx com `event_id` correspondente confirma o recebimento dessa captura. A confirmação de falha usa `ok=true`. Uma resposta malformada ou de outro evento não libera o framebuffer; o mesmo envio será repetido até confirmação/expiração. Recebimento da foto **não** significa que a IA aprovou a peça. A análise e a decisão de liberar pertencem ao servidor e ao evento correto da placa do motor.

O firmware nunca usa “a última foto” de um evento diferente. Mantém a imagem e a reserva em RAM até confirmação ou expiração, sem fazer nova captura durante os reenvios. Não reserva outro evento enquanto guarda o JPEG atual. A validade é verificada tanto pelo relógio UTC quanto por duração monotônica calculada no recebimento; o servidor continua sendo a autoridade final de expiração.

## Falhas e reenvios

- Falha de captura/JPEG inválido: envia JSON `{boot_id, lease_token, reason}` para `POST /api/v1/devices/camera/captures/{id}/failure`.
- Falha de rede/5xx/ausência de confirmação: conserva os mesmos bytes e os mesmos IDs e tenta novamente a cada 2 segundos até expirar a reserva.
- HTTP 404/409/410: pedido/reserva terminou ou conflitou; descarta a imagem, sem associá-la a outro pedido.
- HTTP 413/415/422 do upload: registra a falha do mesmo pedido em vez de recapturar silenciosamente com o mesmo identificador.
- HTTP 401/403: bloqueia novas chamadas até corrigir token/configuração e reiniciar.
- PSRAM ausente ou falha de inicialização: informa `ready=false`, não recebe pedidos e tenta inicializar novamente a cada 10 segundos.
- Reinício da câmera: framebuffer é perdido, surge novo `boot_id`; uma foto antiga não é reutilizada. Não há promessa de retomada de upload após reinício sem microSD.
- Perda de rede ou demora da câmera não aprova uma peça. A placa do motor continua dependente da decisão vinculada ao evento no servidor.

Configuração do exemplo: consulta a cada 1 s, timeout de requisição de 10 s, conexão de 5 s, JPEG limitado a 512 KiB e limite defensivo de reserva de 120 s. O servidor deve fornecer uma reserva dentro desse limite; ajustar ambos os lados se for necessária outra política. Respostas HTTP são limitadas a 8 KiB antes de acumular o corpo em RAM. Nenhum log imprime senha, token ou `lease_token`.

## Pinagem interna usada

Não são jumpers entre a câmera e a placa do motor. São as ligações internas da câmera na AI Thinker:

| Sinal | GPIO |
|---|---:|
| PWDN | 32 |
| RESET | Não conectado (`-1`) |
| XCLK | 0 |
| SDA / SIOD | 26 |
| SCL / SIOC | 27 |
| D0, D1, D2, D3 | 5, 18, 19, 21 |
| D4, D5, D6, D7 | 36, 39, 34, 35 |
| VSYNC | 25 |
| HREF | 23 |
| PCLK | 22 |
| Flash opcional | 4 |

Fonte: [pinagem oficial do exemplo CameraWebServer da Espressif](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h).

## Validação

Compilado em 08/11/2026 com Arduino CLI, **Arduino-ESP32 3.3.12**, placa `esp32:esp32:esp32cam` e **ArduinoJson 7.4.3**, usando uma cópia temporária da configuração de exemplo, sem credenciais reais. Resultado: **1.158.405 bytes de flash (36%)** e **60.952 bytes de variáveis globais (18%)**. A configuração temporária foi removida; os arquivos de rede reais devem ser preenchidos localmente antes de compilar para a placa do usuário.

Houve revisão do contrato com o backend, mas não gravação de placa nem ensaio físico. Antes do teste final: conferir foco/iluminação e que cada captura aparece no evento correto; simular câmera desconectada, upload repetido, reserva expirada, resposta perdida e reinício, sempre verificando que não há liberação indevida do motor. Compilação não comprova estabilidade elétrica, qualidade da fotografia, rede ou precisão do modelo.
