# Validação da Versão 4 — 08/11/2026

## Servidor e interface

- **37 testes Python aprovados**, incluindo integração com PostgreSQL 16.15 real, isolado em `127.0.0.1` e banco de teste. Cobrem sessão, tokens separados, comandos/ACK, ciclo, duplicação de upload, boot antigo, parada, expiração e resultado tardio; novos testes verificam home/painel, fronteiras públicas, catálogo, acesso de usuário inativo, imagens e ausência de credenciais padrão.
- **Três arquivos de testes Node aprovados**: `factory-ui.test.cjs`, `app.test.cjs` e `pages.test.cjs`. Cobrem estados dos controles, polling, logout, prévia sem comandos reais e estrutura das novas páginas. Sintaxe dos scripts conferida.
- Home e painel abertos em navegador local. Botões Calibrar/Iniciar/Parar visíveis e desabilitados na prévia, aviso de demonstração, módulos e estados conferidos. Home também conferida em viewport 390 × 844, sem transbordamento horizontal.
- Resultados de reconhecimento nos testes de fluxo são controlados pela suíte; não medem precisão do modelo YOLOv8.

As dependências de testes emitem aviso de depreciação de TestClient/httpx; os testes passaram com as versões fixadas.

## Firmwares compilados

Arduino CLI oficial, Arduino-ESP32 **3.3.12**, ArduinoJson **7.4.3**, bundle CA público habilitado, sem credenciais reais nos ensaios:

| Firmware | FQBN | Flash | Globais |
|---|---|---|---|
| Esteira V4 | `esp32:esp32:esp32` | 1.139.503 bytes (86%) | 49.596 bytes (15%) |
| ESP32-CAM V4 | `esp32:esp32:esp32cam` | 1.229.273 bytes (39%) | 60.960 bytes (18%) |

A compilação final do motor usou SSID/token fictícios não vazios para incluir o caminho de rede/HTTPS, que pode ser eliminado pelo otimizador com configuração vazia. Os `config.h` temporários foram removidos após conferência. Nenhuma placa foi gravada.

## Configuração e publicação

Segredos novos gerados localmente com fonte criptográfica; cinco valores distintos de 32 bytes aleatórios. Tokens do `.env` e dos respectivos `config.h` privados conferidos sem imprimir os valores. Configurações reais são ignoradas pelo Git; exemplos públicos usam marcadores. Versões entregues anteriormente preservadas.

O domínio resolve por DNS, mas a verificação HTTPS retornou `RemoteCertificateNameMismatch`. Não foi desativada a validação TLS. Foram incluídos exemplos de Nginx e Caddy para configurar certificado correto; não houve alteração do servidor existente.

## Não executado / pendente

- Docker build e instalação na VPS; Docker não está disponível neste computador.
- Inferência real: falta `best.pt` treinado e mapa definitivo de componentes.
- Medição de latência, consumo de memória e precisão na VPS real.
- Gravação de placas, teste de Wi-Fi, foco/iluminação e operação física completa.
- Correção do certificado do domínio e confirmação de HTTPS válido.
- Confirmação de alimentação adequada ao motor, divisor ECHO e emergência física.

## Ensaio físico proposto

Com alimentação adequada e motor inicialmente desabilitado, conferir calibração/sensor, comunicação autenticada e reserva de captura. Depois testar uma peça por vez: reconhecida, desconhecida, ambígua e peça que permanece no sensor. Simular rede desligada, câmera indisponível, worker parado, análise lenta, resultado de boot anterior e reinício durante o ciclo. Nenhuma dessas falhas pode aprovar movimento. Registrar o resultado real antes de declarar o conjunto validado.

## Tentativa de gravação da ESP32-CAM — 08/11/2026

Log enviado pelo usuário: compilação concluída, 1.229.353 bytes de flash (39%) e 60.960 bytes globais (18%). O esptool 5.3.1 conectou à COM4, mas durante o envio do stub ocorreu erro pySerial `Cannot configure port`, `PermissionError(13)`, acesso negado pelo Windows. A gravação não foi concluída; o log não confirma execução do firmware, câmera pronta ou comunicação com a VPS.

O Windows identifica a COM4 como adaptador USB serial FTDI. Foi orientado fechar programas que usam a porta, reconectar o USB, confirmar a porta e tentar Upload Speed 115200, com cabo de dados e conexão USB direta. Persistindo, conferir alimentação e driver FTDI oficial. Causa ainda não determinada; nenhuma configuração de driver foi alterada pelo assistente.

O aviso de cristal estimado em 0,46 MHz, normalizado para 26 MHz, não confirma a frequência física do cristal nem defeito na placa. Não alterar cristal ou frequência de flash com base nesse aviso. Referências: [Espressif — erros seriais](https://docs.espressif.com/projects/esptool/en/latest/esp32/troubleshooting.html#a-serial-exception-error-occurred) e [menu Upload Speed](https://docs.espressif.com/projects/arduino-esp32/en/latest/guides/tools_menu.html#upload-speed).

## Diagnóstico da base ESP32-CAM-MB — 08/11/2026

O usuário confirmou que o ESP32 comum grava pela COM3 e a câmera usa uma base ESP32-CAM-MB na COM4. A numeração diferente é normal. Consulta do Windows: COM4 identificada como FTDI, driver 2.12.36.20, ProblemCode 0. Isso confirma reconhecimento do dispositivo, sem comprovar estabilidade do driver/adaptador.

A Arduino IDE mostrou novamente `Cannot configure port`/acesso negado e também uma notificação `Serial port busy`. Foi cancelada pela interface uma tentativa que já havia retornado erro. Nenhuma placa foi gravada, nenhum driver ou firmware foi alterado; o problema permanece em diagnóstico.

Correção da orientação anterior sobre velocidade: o perfil AI Thinker instalado não oferece menu Upload Speed e define upload em 460800 no boards.txt. Não foi alterado esse arquivo. Para um ensaio serial da base isolada pode-se usar 115200, sem confundir a velocidade do Monitor Serial com a velocidade de gravação.

Próximo teste pendente: desconectar USB, desencaixar a ESP32-CAM da MB e reconectar só a base vazia; testar abertura da COM4. O usuário informou que a câmera ainda está encaixada; a abertura da porta pelo assistente foi adiada. Falha também com base vazia aponta para o caminho USB/driver/base; abertura estável permite investigar depois encaixe, alimentação e comunicação com a câmera. Não há confirmação de defeito na câmera ou na base.

## Ensaios de acesso serial da câmera — 08/11/2026

- O usuário retirou a ESP32-CAM da base MB. A primeira abertura da COM4 falhou enquanto havia Monitor Serial ativo. Após fechar efetivamente a aba do monitor, a base vazia abriu em 115200, aceitou 460800 e voltou a 115200, sem transmitir dados. Isso valida apenas esse ensaio da interface serial em repouso, não a gravação ou a câmera completa.
- Com a câmera novamente encaixada, uma nova gravação pela Arduino IDE falhou durante `Uploading stub flasher`, com `Cannot configure port` e erro Windows 5. Estimativas de cristal e identificação variaram entre tentativas; não foram usadas para alterar cristal, flash, eFuses ou firmware.
- Foram feitos ensaios de consulta ROM `read-mac`, sem stub nem escrita de flash, em 115200 e com a IDE fechada. Tanto esptool 5.3.1 do Arduino quanto esptool 4.11.0 oficial instalado em pasta isolada falharam na conexão com a mesma classe de erro pySerial. Algumas tentativas deixaram processo pendente, exigindo reconectar o USB para liberar a interface.
- A porta variou entre COM4 e COM5 depois de reconexões do usuário. Usar sempre a porta atualmente enumerada. O usuário confirmou que o cabo funcionou ao gravar o ESP32 comum; esse dispositivo usa CH9102, enquanto a base da câmera aparece como FTDI.
- Driver FTDI instalado: 2.12.36.20, sem código de problema permanente no PnP. Nenhum driver foi alterado. A sessão do assistente não tem elevação administrativa do Windows; uma reinstalação do driver deverá ser executada pelo usuário como administrador.
- Gravação da ESP32-CAM continua pendente. Não há diagnóstico conclusivo de defeito na câmera ou base, nem validação de captura/reconhecimento. Próximos passos: reinstalação do pacote FTDI oficial e novo ensaio; persistindo, comparar outra base/conversor e verificar alimentação/encaixe.
