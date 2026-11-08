# Esteira V3 — reconhecimento antes da saída

Código atual: [esteira-v3/esteira-v3.ino](esteira-v3/esteira-v3.ino). O antigo Teste Motor 5 nesta pasta é referência preservada; não é o firmware integrado.

## Configuração e gravação

1. Instalar Arduino-ESP32 **3.3.12** e ArduinoJson **7.4.3**. Usar ESP32 Dev Module para a placa ESP32 clássica compatível.
2. Copiar `config.example.h` para `config.h`, preencher Wi-Fi, URL HTTPS sem barra final, `MOTOR_API_TOKEN` e CA do certificado da VPS. `config.h` não deve ir ao GitHub.
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

Compilação realizada com core 3.3.12/ArduinoJson 7.4.3 para `esp32:esp32:esp32`. O resultado final e os testes de servidor estão em [VALIDACAO.md](../VALIDACAO.md). Não houve gravação nem ensaio físico desta versão.
