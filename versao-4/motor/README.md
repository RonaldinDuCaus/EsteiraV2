# Esteira V4 — reconhecimento antes da saída

Código atual: [esteira-v4/esteira-v4.ino](esteira-v4/esteira-v4.ino). O antigo Teste Motor 5 nesta pasta é referência preservada; não é o firmware integrado.

## Configuração e gravação

1. Instalar Arduino-ESP32 **3.3.12** e ArduinoJson **7.4.3**. Usar ESP32 Dev Module para a placa ESP32 clássica compatível.
2. Copiar `config.example.h` para `config.h`, preencher Wi-Fi e `MOTOR_API_TOKEN` da Versão 4. A URL pública já é `https://minifabrica.kronux.com.br`. O bundle de CAs públicas do core 3.3.12 está habilitado; preencher `SERVER_CA` é opcional para uma cadeia privada/customizada. `config.h` não deve ir ao GitHub.
3. Gravar com a alimentação do motor desconectada. Monitor Serial em 115200 baud.
4. O programa conecta ao Wi-Fi e servidor, mas inicia desautorizado. Na dashboard, retirar todas as peças e clicar **Calibrar**. Aguardar confirmação da placa e área livre estável.
5. Depois de câmera e YOLO prontos, clicar **Iniciar** uma vez. Reinício, falha ou parada exigem nova autorização.

Não há mais `g` ou `c` pelo Serial; os botões enviam esses comandos pela API. Serial `p` continua disponível como parada local de software. Isso não substitui emergência física independente.

## Ligações mantidas

| Sinal | ESP32/destino |
|---|---|
| PWMA | D25 / GPIO25 |
| AIN1 | D26 / GPIO26 |
| AIN2 | D27 / GPIO27 |
| STBY | D33 / GPIO33 |
| VCC do TB6612 | 3V3 |
| VM do TB6612 | Alimentação adequada ao motor de 5 V informado |
| A1/A2 | Fios do motor |
| BIN1/BIN2/PWMB | GND |
| TRIG do HC-SR04 | D18 / GPIO18 |
| ECHO do HC-SR04 | D19 via divisor 2,2 kΩ em série e 3,3 kΩ ao GND |
| VCC do HC-SR04 convencional | 5 V regulados |
| GND | Comum entre ESP32, driver, sensor e negativo da alimentação |

O modelo exato do ultrassônico/placa ainda precisa ser conferido. O último relato manteve 8–8,4 V em VM apesar do motor informado como 5 V; não energizar a 100% nessa condição. Adequação de alimentação, divisor ECHO e corrente de partida continuam pendentes de confirmação.

## HTTPS do domínio configurado

A Versão 4 usa `TLS_USE_BUILTIN_CA_BUNDLE=true` por padrão, com o bundle completo embutido no Arduino-ESP32 3.3.12. `SERVER_CA` em PEM, se preenchida, tem prioridade. A cadeia do certificado, o nome do domínio e o relógio NTP continuam sendo verificados; não há `setInsecure()` nem exceção para certificado incorreto.

Na verificação do domínio desta entrega foi observado `RemoteCertificateNameMismatch`. Isso indica que o certificado apresentado não corresponde ao hostname e deve ser corrigido no proxy/servidor. O bundle não corrige erro de hostname; a placa deve continuar sem autorizar movimento enquanto a conexão validada não funcionar.

O firmware informa `firmware_version=esteira-v4.0`. O contrato das rotas e a máquina de estados permanecem os da Versão 3. Exemplos públicos não contêm tokens reais.

## Máquina de estados

`disabled → calibrating → ready → moving → settling → awaiting_analysis → exiting → completing → moving`

- Abaixo do fundo menos 20 mm: freia e cria um ID único para a peça. Aguardar 500 ms de estabilização antes de solicitar captura pelo servidor.
- Enquanto a análise estiver pendente, motor parado. **Cinco segundos não liberam mais a esteira.**
- Apenas `recognized` + `approved=true`, com o mesmo `boot_id` e `event_id` e autorização atual, permite saída.
- Na saída, pode movimentar enquanto a peça ainda ocupa o sensor; precisa de oito leituras de área livre. Limite inicial de 3 s; se não sair, entra em falha.
- Ao confirmar a saída no servidor, continua procurando a próxima peça, sem pedir nova partida a cada ciclo.
- Desconhecido, erro ou cancelamento: conferência, sem movimento automático. Recuperação: **Parar → remover peça → Calibrar → Iniciar**.
- Sensor inválido, perda de comunicação por 3 s ou análise acima de 60 s: parada e revogação local. Reconectar não inicia sozinho.
- Comandos têm validade e pertencem ao boot atual. Comandos anteriores à última falha/parada local são rejeitados. A rede roda em tarefa separada; o sensor não espera uma chamada HTTP terminar.

`MOTOR_PWM_PERCENT=100` preserva o acionamento que o usuário relatou funcionar. É ajuste inicial; frenagem, velocidade, distância de parada e tempo de saída precisam de ensaio físico. Sem encoder, `motor_on` reporta saída GPIO acionada, não medição de rotação.

## Validação

Compilado em 08/11/2026 com core **3.3.12**, ArduinoJson **7.4.3** e placa `esp32:esp32:esp32`, com bundle CA público habilitado. O ensaio final de compilação usou SSID/token **fictícios não vazios**, para que o caminho de rede/HTTPS não fosse eliminado pelo otimizador. Resultado: **1.139.503 bytes de flash (86%)** e **49.596 bytes de variáveis globais (15%)**. O config.h temporário foi removido; nenhuma credencial real foi lida ou incluída nessa compilação.

O resultado da entrega e os testes do servidor estão em [VALIDACAO.md](../VALIDACAO.md). Não houve gravação nem ensaio físico desta versão. Compilação não comprova conexão com o domínio enquanto seu certificado estiver incorreto, compatibilidade elétrica ou precisão de parada.
