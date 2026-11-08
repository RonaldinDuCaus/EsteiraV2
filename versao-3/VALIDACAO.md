# Validação da Versão 3 — 08/11/2026

## Automatizado

- **27 testes Python aprovados**: 15 testes de política/contrato e 12 com PostgreSQL 16.15 real, isolado em localhost e banco descartável. Incluem login, sessão, botão autenticado, isolamento de tokens, primeiro calibrar sem referência, origem HTTPS atrás de proxy, ciclo com resultado controlado, evento/foto duplicados, bytes conflitantes, placa reiniciada, boot aposentado, comando expirado, análise tardia, parada depois de reconhecer, falha da câmera e recuperação de evento local recusado.
- **2 scripts de testes Node aprovados**, com várias asserções: bloqueios dos botões, pedido sem falsa confirmação, polling único, cancelamento no logout e prévia sem chamadas reais.
- Sintaxe Python e JavaScript conferida.
- Modelo YOLO real foi substituído somente no ponto de resultado dos testes de fluxo. Não há medição de precisão nesta suíte.

A biblioteca de testes emite um aviso de depreciação de TestClient/httpx; as versões estão fixadas e os testes passaram. Isso não afetou o resultado executado.

## Firmwares compilados

Arduino CLI oficial, Arduino-ESP32 **3.3.12**, ArduinoJson **7.4.3**, configurações de exemplo sem credenciais reais:

| Firmware | FQBN | Flash | Globais |
|---|---|---|---|
| Esteira V3 | esp32:esp32:esp32 | 914.165 bytes (69%) | 46.676 bytes (14%) |
| ESP32-CAM V3 | esp32:esp32:esp32cam | 1.158.405 bytes (36%) | 60.952 bytes (18%) |

A câmera exige AI Thinker/OV2640/PSRAM, modelo confirmado pelo usuário. O ESP32 comum segue a pinagem usada nos testes anteriores. Compilar não confirma a montagem elétrica nem a operação física.

## Interface

Prévia demonstrativa aberta no navegador local: Calibrar/Iniciar/Parar visíveis, aviso de demonstração e comandos desativados, cartões de motor/câmera/YOLO, pedido/ACK e evento. A prévia usa dados demonstrativos e não comprova comunicação com placas. As chamadas reais são verificadas nos testes da API/UI.

## Não executado / pendente

- Gravação de placas e ensaio físico da Versão 3.
- Inferência real YOLOv8: falta o modelo treinado e mapa definitivo de componentes.
- Avaliação de conhecidos/desconhecidos, falsos aceites, rejeições e ambiguidades nas peças reais.
- Docker build/instalação na VPS, recursos e tempo de inferência da VPS.
- Domínio, proxy HTTPS, CA, Wi-Fi e tokens reais.
- Confirmação da alimentação regulada do motor, divisor ECHO, corrente de partida e emergência física.

## Ensaio físico proposto

Com a alimentação adequada, testar primeiro calibração e sensor com motor desabilitado. Depois verificar reconhecimento/erro com uma peça de cada vez, saída sem travamento e distância de frenagem. Simular Wi-Fi desligado, câmera desconectada, worker parado, resultado lento e reinício durante o ciclo. Nenhuma dessas falhas pode aprovar uma peça. Só declarar validado após registrar o resultado real do ensaio.
