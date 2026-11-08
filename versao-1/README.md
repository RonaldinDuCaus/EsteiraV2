# Versão 1 — base do motor com ultrassônico

Data: 08/11/2026. Primeira versão completa dos arquivos novos disponíveis deste projeto; não significa sistema completo implementado. A numeração da versão é do conjunto, independente do antigo nome Teste Motor 5.

## Conteúdo e estado

| Parte | Arquivo / situação |
|---|---|
| Motor/esteira | [Teste Motor 5](motor/teste-motor-5-ciclo/teste-motor-5-ciclo.ino), copiado sem alterações |
| Câmera | Ainda não incorporada; teste OV7670 adiado |
| Site/backend | Dashboard existente na VPS, ainda não importada/revisada neste conjunto |
| Integração | Motor e ultrassônico no sketch; câmera e API ainda não integradas |

Esta versão preserva o código atual para teste. A única versão de acionamento confirmada fisicamente pelo usuário continua sendo o antigo Teste Motor 1 (5 s ligado / 5 s desligado). O Teste Motor 5 não foi confirmado como validado fisicamente e não foi compilado pelo assistente.

## Operação prevista

Abrir `motor/teste-motor-5-ciclo/teste-motor-5-ciclo.ino` na Arduino IDE com suporte ESP32 da Espressif. Selecionar placa/porta compatíveis com o ESP32 clássico utilizado. Monitor Serial: 115200 baud.

1. Calibrar com esteira vazia e motor parado enviando `c`.
2. Após calibração e área livre estável, enviar `g` uma vez.
3. Ao detectar peça, frear e aguardar pelo menos 5 segundos.
4. Quando a peça sair e houver oito leituras livres consecutivas, retomar automaticamente.
5. Repetir enquanto a sessão estiver autorizada. `p` cancela; reiniciar exige `c` e `g` novamente.

Uma leitura inválida para o motor, mas conserva a autorização da sessão; a retomada exige recuperação de área livre estável e cumprimento da pausa mínima. Peça que continua no sensor mantém a parada. Não há saída controlada de uma peça ainda ocupando o sensor, fotografia, análise ou aprovação por servidor neste teste.

## Ligações desta versão

| Componente / sinal | ESP32 / destino |
|---|---|
| TB6612FNG PWMA | GPIO25 / D25 |
| TB6612FNG AIN1 | GPIO26 / D26 |
| TB6612FNG AIN2 | GPIO27 / D27 |
| TB6612FNG STBY | GPIO33 / D33 |
| TB6612FNG VCC | 3V3 |
| TB6612FNG VM | Alimentação adequada ao motor de 5 V informado |
| TB6612FNG A1/A2 | Dois fios do motor |
| TB6612FNG BIN1/BIN2/PWMB | GND |
| TB6612FNG B1/B2 | Sem conexão |
| Ultrassônico TRIG | GPIO18 / D18 |
| Ultrassônico ECHO | GPIO19 / D19 via divisor, nunca 5 V direto |
| Ultrassônico VCC | 5 V regulados para HC-SR04 convencional |
| Todos os GND | Terra comum, negativo do motor direto ao driver |

Divisor: ECHO → resistor 2,2 kΩ → ponto ligado ao D19 → resistor 3,3 kΩ → GND. Confirmar modelo do ultrassônico, placa e alimentação antes de energizar. Câmera desconectada.

## Parâmetros e pendências

- `SPEED_PERCENT=100`: requer alimentação adequada ao motor de 5 V; o usuário confirmou bateria de 8–8,4 V ainda no VM, portanto não energizar nessa condição. A adequação segue pendente.
- Instalação do divisor ECHO ainda não confirmada após relato de conexão direta.
- `PAUSE_MS=5000`, `BRAKE_MS=300`, intervalo entre medições de 65 ms.
- Detecção: distância do fundo menos 20 mm; área livre: fundo menos 10 mm. Valores precisam de ensaio com as peças reais.
- Corrente de partida/travamento, frenagem e emergência física ainda precisam de avaliação.
- Retomada temporizada é apenas para bancada; no sistema final, tempo decorrido não aprova peça nem substitui resultado de análise.

## Histórico desta versão

- Criada a organização por versões completas, a pedido do usuário.
- Copiado o Teste Motor 5 byte a byte; nenhuma alteração funcional.
- Código e ligações anteriores preservados nas pastas de testes da raiz.

Para qualquer próxima mudança funcional, criar `versao-2` a partir desta versão, com cópias dos componentes existentes e README próprio. Acrescentar câmera/site somente quando houver arquivos reais. Não usar vínculos simbólicos para arquivos mutáveis de outras versões.
