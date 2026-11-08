# Projeto Esteira IoT

Controle de uma esteira com ESP32, driver TB6612FNG e detecção de peças, com futura integração à dashboard existente em uma VPS Linux.

**Última atualização:** 08/11/2026 (America/Sao_Paulo).

## Organização por versões completas

A partir de 08/11/2026, cada entrega de código/configuração será salva em `versao-1`, `versao-2`, `versao-3` etc. Cada pasta reúne as partes existentes do projeto (`motor/`, futuramente `camera/` e `site/`) e um README próprio. A versão anterior não será sobrescrita.

**Versão atual organizada:** [Versão 3 — integração com YOLOv8](versao-3/README.md). [Esteira](versao-3/motor/README.md), [ESP32-CAM](versao-3/camera/README.md), [site e worker](versao-3/site/README.md), [protocolo](versao-3/conexoes-esp32/README.md) e [validação](versao-3/VALIDACAO.md).

A Versão 1 copia o Teste Motor 5 sem mudanças funcionais. Não há arquivos de câmera/site incorporados ainda. A Versão 2 importou o ZIP da Etapa 1 em site/ e separou a documentação das conexões ESP32; o motor foi copiado sem alterações. A Versão 3 integra firmware, comandos e análise YOLOv8; a próxima alteração será a Versão 4. As pastas `teste-motor-*` da raiz permanecem como histórico anterior.

O README da raiz continua sendo o índice e acompanhamento geral. O procedimento permanente está em [AGENTS.md](AGENTS.md). Documentar uma nova observação de teste não exige duplicar todos os códigos.

## Ideia do projeto

A Esteira IoT integra transporte de módulos eletrônicos, detecção de presença e reconhecimento de imagens. O objetivo é: operador autoriza o início → esteira transporta a peça → sensor detecta → motor para na região da câmera → câmera envia fotografia vinculada ao evento → servidor na VPS Linux identifica entre os componentes ativos cadastrados → dashboard e LCD mostram o resultado → peça aprovada recebe saída controlada. Resultado desconhecido, ambíguo ou falha mantém a parada para conferência. Não há separador físico por categorias confirmado.

A dashboard existente já recebe/reconhece fotos e gerencia inventário, conforme relato do usuário. A operação final deverá funcionar sem computador local, com placas conectadas à rede. A Versão 3 agora contém câmera, API e integração em código; configuração real, modelo treinado, LCD, emergência física e validação do conjunto ainda são pendências. Testes de bancada não equivalem à validação da instalação final.

## Onde estamos

- **Motor e driver: funcionamento confirmado pelo usuário.** O último teste gira por 5 segundos e desliga por 5 segundos, repetidamente.
- **Código atual validado em bancada pelo usuário:** [Teste motor 1](teste-motor-1/teste-motor-1.ino).
- **Código atual:** [Versão 3 / Esteira V3](versao-3/motor/esteira-v3/esteira-v3.ino) + [ESP32-CAM V3](versao-3/camera/esp32cam-v3/esp32cam-v3.ino). O motor só recebe saída controlada após aprovação do mesmo evento/boot. Não há mais liberação por 5 segundos. Ambos compilaram; ensaio físico e pesos treinados pendentes.
- **Pendências elétricas imediatas:** usuário confirmou que VM permanece na bateria de 8–8,4 V, embora o motor tenha sido informado como 5 V; não energizar os Testes 4 e 5 a 100% nessa condição. Usar alimentação regulada de 5 V adequada à corrente de partida ou confirmar especificação real do motor. A instalação do divisor no ECHO também segue sem confirmação após relato de ligação direta ao D19. Não há confirmação de dano ao ESP32.
- A Versão 3 implementa os botões Calibrar/Iniciar/Parar, API de dispositivos, captura vinculada, worker YOLOv8 e migração aditiva. Ainda não foi implantada na VPS; falta o detector treinado best.pt, o mapa de classes e a configuração real das placas. O pacote da Versão 2 permanece como referência da Etapa 1.

## Arquivos e versão de referência

```text
Projeto Esteira IoT/
├── README.md
├── AGENTS.md
├── versao-3/
│   ├── README.md / VALIDACAO.md
│   ├── motor/esteira-v3/
│   ├── camera/esp32cam-v3/
│   ├── site/
│   └── conexoes-esp32/
├── versao-2/
│   ├── README.md
│   ├── ORIGEM.json
│   ├── site/
│   ├── conexoes-esp32/
│   └── motor/
├── versao-1/
│   ├── README.md
│   └── motor/
│       └── teste-motor-5-ciclo/
│           └── teste-motor-5-ciclo.ino
├── teste-motor-1/
│   └── teste-motor-1.ino
├── teste-motor-2-ultrassonico/
│   └── teste-motor-2-ultrassonico.ino
├── teste-motor-3-pausa/
│   └── teste-motor-3-pausa.ino
├── teste-motor-4-partida/
│   └── teste-motor-4-partida.ino
└── teste-motor-5-ciclo/
    └── teste-motor-5-ciclo.ino
```

Pasta local: `C:\Users\Rdyxava\Documents\Projeto Esteira IoT`.

Sketch histórico com funcionamento confirmado: `C:\Users\Rdyxava\Documents\Projeto Esteira IoT\teste-motor-1\teste-motor-1.ino`.

O link relativo acima funciona no GitHub. O arquivo foi copiado sem alterações do teste que funcionou em `C:\Users\Rdyxava\Documents\Site\teste-motor-automatico\teste-motor-automatico.ino`.

Esta é uma cópia de referência preservada. Novos ensaios devem seguir as pastas versao-N com README próprio; mudar o código atual validado somente após confirmação do resultado. O repositório remoto atual é EsteiraV2; o histórico desta preparação está registrado na seção GitHub.

## Hardware informado

| Item | Situação |
|---|---|
| ESP32 com pinos identificados com D | Usado no teste; modelo exato da placa ainda não confirmado |
| TB6612FNG | Usado no teste que funcionou |
| Motor DC amarelo de carrinho | Informado pelo usuário como 5 V; corrente nominal e de travamento desconhecidas |
| Duas células 18650 | Usuário mediu aproximadamente 8 a 8,2 V em VM; conjunto chega a 8,4 V carregado |
| Alimentação do ESP32 | USB |
| KY-008, 650 nm | Emissor escolhido; não mede distância nem detecta peças sozinho |
| Sensor de cor | Inscrição informada: Color Sensor V575; pinos GND, OE, S1, S0 (dito SO), S3, S2, OUT, VCC. Chip ainda não confirmado; teste adiado |
| IR receiver | Disponível; modelo e compatibilidade com laser vermelho desconhecidos |

## Ligações atuais do driver

Os nomes D25, D26 etc. são tratados no código como GPIO25, GPIO26 etc. Conferir essa correspondência na placa utilizada.

### Lado esquerdo, de cima para baixo

| TB6612FNG | Destino |
|---|---|
| PWMA | ESP32 D25 / GPIO25 |
| AIN2 | ESP32 D27 / GPIO27 |
| AIN1 | ESP32 D26 / GPIO26 |
| STBY | ESP32 D33 / GPIO33 |
| BIN1 | GND comum |
| BIN2 | GND comum |
| PWMB | GND comum |
| GND | GND do ESP32 / placa de expansão |

### Lado direito, de cima para baixo

| TB6612FNG | Destino |
|---|---|
| VM | Positivo da alimentação externa do motor |
| VCC | 3V3 do ESP32 |
| GND | Negativo da alimentação externa |
| A1 | Primeiro fio do motor |
| A2 | Segundo fio do motor |
| B2 | Sem conexão |
| B1 | Sem conexão |
| GND | GND comum |

Todos os GND são comuns. O negativo da alimentação do motor deve chegar diretamente ao driver. O positivo externo não vai ao VCC nem ao ESP32.

**Pendência elétrica:** o motor foi informado como 5 V, mas foram medidos cerca de 8 V em VM. O funcionamento relatado não valida essa combinação. O sketch usa 100% de acionamento e foi preparado para alimentação regulada de 5 V adequada à corrente do motor. Não houve confirmação de que essa adequação foi feita. Conferir também proteção/carregamento do conjunto 18650 e corrente de partida antes de concluir a validação elétrica.

## Teste motor 1

1. Desconectar a alimentação do motor antes de gravar e manter a câmera desconectada.
2. Abrir `teste-motor-1/teste-motor-1.ino` na Arduino IDE, com suporte ESP32 da Espressif.
3. Selecionar a placa e porta corretas. ESP32 Dev Module é a opção prevista para ESP32 clássico compatível; confirmar modelo.
4. Gravar. Monitor Serial: 115200 baud.
5. Com alimentação do motor adequada, observar: 5 segundos desligado após início, 5 segundos ligado, 5 segundos desligado, repetidamente.

Não exige comando serial e começa a movimentar automaticamente. É somente um teste de bancada, não firmware final da esteira. Ao desligar, STBY vai a LOW e o motor para por inércia, sem frenagem ativa. O estado impresso é o comando do programa, não medição de rotação.

## Proposta anterior, adiada: barreira com KY-008

Fluxo desejado: após autorização de início, motor gira continuamente; uma peça interrompe o feixe entre emissor e receptor; ESP32 manda parar e mantém a esteira parada aguardando liberação.

O KY-008 apenas emite o feixe. O receptor deve ficar do outro lado da esteira e fornecer um sinal utilizável pelo ESP32. Inicialmente o usuário informou possuir somente o emissor; depois informou um sensor de cor e um IR receiver. Ainda não há receptor confirmado como compatível. Não definir pinagem de receptor, polaridade, alimentação ou código final por suposição.

Antes da integração:

- Escolher receptor sensível ao laser vermelho de 650 nm e conferir tensão de alimentação e saída compatível com lógica de 3,3 V.
- Confirmar a versão/pinagem do emissor; a marcação S não deve ser presumida como saída de detecção.
- Testar alinhamento, luz ambiente, peças pequenas e interrupção permanente do feixe.
- Tratar ausência do feixe como condição de parada, inclusive desalinhamento ou emissor desligado.
- Avaliar frenagem elétrica e distância real de parada; ela não será instantânea mecanicamente.
- Evitar exposição dos olhos ao feixe e reflexos; montar o feixe com terminação no receptor.

O HW-201 não é a escolha atual: o usuário relatou dificuldades de ajuste e prefere deixá-lo como último recurso. O ultrassônico passou a ser a prioridade atual por solicitação do usuário.

## Avaliação anterior dos sensores, adiada — 07/11/2026

Proposta ainda não implementada: identificar o sensor de cor e avaliar sua leitura de luz vermelha como receptor experimental do KY-008, em lados opostos da esteira. Fazer primeiro um ensaio com motor desligado, comparando feixe livre e bloqueado, luz ambiente, saturação e tempo de resposta. Só integrar ao motor se houver separação confiável entre as leituras. Outra possibilidade é usar o sensor de cor para detectar contraste com o fundo, sujeita às cores das peças.

O IR receiver precisa ser identificado. Se for receptor demodulado de controle remoto, como TSOP/VS1838, foi projetado para infravermelho modulado e não é um receptor adequado para o feixe vermelho contínuo do KY-008. Um fototransistor/fotodiodo simples é outro caso e depende da resposta espectral e do circuito. Não assumir que qualquer componente de três pinos detecta peças; o pino S do KY-008 não é saída de presença.

Para retomar esta alternativa no futuro: identificar o chip do sensor de cor e o modelo do IR receiver. O usuário quer priorizar os componentes disponíveis e manter HW-201 como último recurso. Código e ligações do motor permanecem os mesmos.

Referências consultadas:

- [Sensor RGB e luz total TCS34725, ams OSRAM](https://ams-osram.com/products/sensor-solutions/ambient-light-color-spectral-proximity-sensors/ams-tcs34725-color-sensor)
- [Receptores de controle remoto TSOP382/384, Vishay](https://www.vishay.com/docs/82491/tsop382.pdf)

## Etapa atual: avaliar ultrassônico — 07/11/2026

O usuário solicitou priorizar ultrassônico para detectar peças, inclusive escuras. Informou largura interna entre paredes de 85,7 mm e sugeriu detecção quando a distância cair mais de 5%.

Cálculo proposto: 85,7 × 0,95 = 81,415 mm, uma redução de 4,285 mm. Esse é apenas um limiar inicial de hipótese, não uma calibração validada. A referência deve ser medida pelo próprio sensor instalado, desde sua face acústica até a superfície de fundo, e pode diferir da largura interna da esteira.

Modelo do ultrassônico ainda desconhecido. Se for HC-SR04 comum, a documentação indica distância mínima de 20 mm, precisão anunciada de até 3 mm e intervalo recomendado superior a 60 ms entre disparos. A margem de 4,285 mm é pequena e precisa de ensaio. Peças pequenas, orientação desfavorável, zona cega e ecos das paredes podem causar falhas. Ultrassônico não depende do contraste de cor, mas isso não garante detecção de qualquer peça.

A parada não será instantânea: há tempo de amostragem, decisão e frenagem mecânica. Exemplo apenas ilustrativo: a 100 mm/s, 60 ms equivalem a 6 mm de avanço antes de considerar a frenagem. Testar velocidade baixa, posição do sensor antes do ponto desejado sob a câmera e frenagem elétrica. Manter a parada travada até autorização; timeout/leitura inválida não devem ser interpretados como caminho livre. O código atual de motor para por inércia e ainda não foi alterado.

Próximo passo: identificar modelo/pinos do ultrassônico e realizar leitura com motor parado. Para modelos com ECHO em 5 V, prever adaptação de nível antes de conectar ao ESP32. Não definir montagem final sem identificar o módulo.

Referência: [Datasheet HC-SR04](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf).

## Montagem proposta do ultrassônico e tolerância

Pinos informados: VCC, TRIG, ECHO e GND. Essa lista não identifica sozinha o modelo. A tabela abaixo vale para um HC-SR04 convencional de 5 V; confirmar inscrição ou foto antes de energizar se houver dúvida. Montar com USB e bateria desconectados e manter a câmera desconectada: GPIO18/19 eram usados no ensaio dela.

| Ultrassônico | Ligação proposta |
|---|---|
| VCC | Alimentação regulada de 5 V, nunca a bateria de 8,4 V |
| TRIG | ESP32 D18 / GPIO18 |
| ECHO | Divisor resistivo abaixo, cujo ponto central vai a D19 / GPIO19 |
| GND | GND comum do ESP32, driver e alimentação |

```text
ECHO --- resistor 2,2 kΩ ---+--- ESP32 D19
                          |
                     resistor 3,3 kΩ
                          |
                         GND
```

O divisor reduz 5 V para aproximadamente 3 V. Não conectar ECHO de 5 V diretamente ao ESP32. Um resistor sozinho em série não equivale a esse divisor. Se houver saída 5 V da placa de expansão proveniente do USB, pode ser avaliada para alimentar o sensor após verificar tensão e configuração; não presumir tensão pelo pino VIN ou por um borne V da expansão. Não alimentar o motor pela saída da placa ESP32.

Proposta inicial para evitar pequenas oscilações: testar uma redução de 20 mm em relação ao fundo medido. Com referência real de 85,7 mm, limiar de presença seria aproximadamente 65,7 mm. É apenas exemplo: se a peça circular entre 65,7 e 85,7 mm da face do sensor, pode não ser detectada. A posição permitida das peças e a zona mínima do sensor devem orientar o ajuste. Não escolher margem grande sem testar a menor peça na posição mais desfavorável.

Proposta de histerese: presença abaixo de 65,7 mm; considerar área livre novamente apenas acima de 75,7 mm, após estabilidade confirmada. Entre os limites, manter o estado anterior. A confirmação de área livre não autoriza reinício automático; manter parada travada após detecção até liberação. Limiar e histerese foram implementados no Teste motor 2; ainda não validados fisicamente. Evitar médias longas que atrasem a parada; calibrar fundo somente com motor parado e área vazia, sem adaptar a referência silenciosamente durante o movimento.

Próximo ensaio: leitura do ultrassônico com alimentação do motor desconectada; depois integração com frenagem e validação da posição final sob a câmera. O Teste motor 1 preservado continua alternando 5 s/5 s e NÃO lê o sensor nem para por presença.

## Teste motor 2: esteira com ultrassônico

Arquivo: [teste-motor-2-ultrassonico.ino](teste-motor-2-ultrassonico/teste-motor-2-ultrassonico.ino).

**Situação:** implementado, mas não compilado nem ensaiado fisicamente pelo assistente. O Teste motor 1 permanece a referência que o usuário confirmou funcionar.

### Correção elétrica antes do ensaio

O usuário relatou ligar TRIG ao GND acidentalmente. TRIG é entrada: isso normalmente apenas mantém o disparo em nível baixo, desde que não tenha ocorrido curto da alimentação ou conflito com um GPIO acionado. A descrição não comprova dano nem ausência de dano.

O usuário também confirmou ECHO diretamente no GPIO19. Para HC-SR04 de 5 V, essa ligação deve ser retirada com a alimentação desligada. Instalar o divisor 2,2 kΩ entre ECHO e GPIO19 e 3,3 kΩ entre GPIO19 e GND. Software não corrige sobretensão no GPIO. Verificar modelo do sensor antes de energizar. Manter a alimentação do motor adequada aos 5 V informados, sem aplicar diretamente a bateria de 8,2 V.

### Operação

1. Com divisor instalado e alimentação adequada, gravar o sketch com a alimentação do motor desconectada.
2. Abrir Monitor Serial em 115200 baud; o programa já imprime distâncias, sem dar partida.
3. Deixar a esteira vazia, sensor fixo e enviar `c`. A calibração usa 32 leituras espaçadas em 65 ms, mediana e rejeição quando a amplitude excede 6 mm. Não há verificação física automática de esteira vazia: o operador deve garantir essa condição.
4. Passar peças manualmente e comparar as distâncias com o limiar impresso, ainda sem motor energizado.
5. Para ensaio de movimento com alimentação adequada, enviar `g`: exige calibração, três leituras de área livre, leitura recente e distância na faixa livre. PWM inicial de 30%, configurável por `SPEED_PERCENT`. Esse valor pode não vencer a carga de partida de alguns motores; não aumentar tensão para compensar.
6. `p` manda parar. `s` mostra o estado; `h` mostra ajuda. Comandos são de um caractere, com ou sem nova linha.

Ao detectar distância menor ou igual ao fundo menos 20 mm, a primeira leitura válida provoca parada travada. Fundo menos 10 mm define a faixa livre, com três leituras para confirmar. Não há média longa durante movimento. Sem eco, ECHO preso alto, distância fora de 20–4000 mm ou fundo mais de 20 mm além do calibrado impedem movimento seguro; quando acionado, o programa manda parar. Nenhum retorno de leitura provoca partida automática.

A frenagem usa IN1=IN2=HIGH e STBY=HIGH por 300 ms, depois desabilita o driver. Os 300 ms são um valor inicial de ensaio, não uma distância/tempo de parada garantido. A leitura usa `pulseIn` com timeout de 25 ms e disparos a cada 65 ms. Isso não é parada instantânea nem emergência física; ajustar velocidade e posição do sensor pelos ensaios reais. O programa não controla câmera, dashboard ou saída controlada de peça nesta etapa.

## Observação do vídeo de bancada — 07/11/2026

Arquivo enviado: `C:\Users\Rdyxava\Downloads\WhatsApp Video 2026-11-07 at 22.46.34.mp4`. Inspeção visual de quadros; áudio não transcrito.

- O Monitor Serial mostra leituras numéricas e mudança de distância durante a apresentação da mão ao sensor. Isso comprova resposta de medição em parte do ensaio, não precisão ou confiabilidade para todas as peças.
- Também aparecem `Distancia: INVALIDA` e valores variáveis (por exemplo, cerca de 67 mm e 157 mm no trecho final). Como há movimentação no ensaio, não atribuir toda variação a ruído com fundo fixo.
- Nos quadros inspecionados aparece `PARADO | SEM LIBERACAO`, sem os campos `Fundo`, `Parar` e `Livre`. Pelo código fornecido, isso indica ausência de calibração válida nesses momentos. Não há evidência visual de parada automática do motor validada.
- A instalação do divisor no ECHO ainda não foi confirmada. Leituras numéricas não comprovam compatibilidade elétrica nem integridade do GPIO.
- Próximo passo: corrigir/confirmar o divisor, fixar sensor e fundo, manter esteira vazia, executar `c` e observar o resultado da calibração. Só após calibração aceita e ensaio manual das peças, testar `g` com alimentação adequada do motor.

## Troca do ultrassônico e clareza das mensagens — 07/11/2026

O usuário substituiu o sensor e relatou leituras entre 96,2 e 96,4 mm. Isso sugere melhora da estabilidade no trecho observado; ainda não confirma calibração aceita, distância exata ou parada por presença. Modelo do sensor substituto e instalação do divisor ainda precisam ser confirmados.

O Teste motor 2 foi atualizado para substituir a mensagem genérica `SEM LIBERACAO` por motivos específicos: falta calibrar (`c`), calibração em andamento, falha de PWM, frenagem, leitura inválida/antiga, área não livre ou pronto para iniciar (`g`). A lógica de detecção e autorização não foi relaxada. Atualização de mensagens não compilada nem testada fisicamente pelo assistente.

Para o código anterior, já é possível enviar `c` com a esteira vazia, aguardar a confirmação de calibração e enviar `g` após área livre. A leitura estável por si só não autoriza partida. A calibração é feita a cada reinicialização e fica apenas na memória RAM. Com fundo calibrado de aproximadamente 96,3 mm, os limites atuais ficam aproximadamente em 76,3 mm para presença e 86,3 mm para área livre. Usar os valores reais impressos pelo programa.

## Teste motor 3: pausa temporizada — 07/11/2026

Nas capturas enviadas, o fundo foi calibrado em 96,2 mm, com presença em 76,2 mm e área livre em 86,2 mm. Leituras de 68,4 e 65,0 mm passaram abaixo do limiar. O estado era PARADO antes e depois da passagem: não havia comando de movimento ativo nos trechos mostrados. As mensagens AREA LIVRE/SEM LIBERACAO correspondem à versão antiga do Teste motor 2, anterior à melhoria das mensagens.

O usuário pediu que a esteira fique parada por alguns segundos ao detectar peça. Criado [Teste motor 3](teste-motor-3-pausa/teste-motor-3-pausa.ino), sem modificar os ensaios anteriores.

- Gravar esta versão com alimentação do motor desconectada; corrigir/confirmar divisor ECHO e alimentação adequada ao motor antes do ensaio.
- Monitor Serial em 115200: enviar `c` com esteira vazia, aguardar calibração e enviar `g` uma vez para iniciar.
- Ao detectar peça: frenagem elétrica e pausa mínima de 5000 ms, contada desde a detecção.
- Após o tempo, retomar apenas com três leituras livres consecutivas e recentes. Se a peça permanecer no sensor, continuar parado. Neste ensaio o operador precisa retirar a peça; saída controlada que movimenta uma peça ainda ocupando o sensor não está implementada.
- `p`, comando inválido, falha de leitura ou fundo fora da faixa cancelam a retomada automática; nova partida requer `g` e condições válidas.
- `c` durante pausa cancela retomada e exige garantir área vazia para recalibrar. Reinício da placa não dá partida automática.
- `PAUSE_MS=5000` define a pausa. PWM permanece em 30%; não há mudança automática da potência. Se aparecer COMANDO MOTOR ATIVO e o eixo não girar, investigar torque/carga/alimentação; as imagens recebidas ainda não mostram essa condição.

A retomada temporizada é apenas para o teste de bancada solicitado. No projeto final, tempo decorrido não aprova uma peça: será necessário resultado da análise ou liberação do operador. A retomada automática só é apropriada ao ensaio supervisionado, e o teste não substitui emergência física.

Verificação: código revisado por leitura; Arduino CLI/compilador não disponíveis neste ambiente. Sem compilação, simulação ou ensaio físico desta versão. Medição por ultrassom tem latência e frenagem exige validação de distância real.

## Teste motor 4: investigar falta de partida — 07/11/2026

O usuário confirmou que o motor não gira mesmo com COMANDO MOTOR ATIVO no Monitor Serial. Isso separa o problema atual da falta de autorização/calibração anterior.

Diferença identificada: Teste motor 1, que girou, usava PWMA permanentemente HIGH (100%). Testes 2 e 3 passaram a PWM de 30%. Esse valor pode não vencer atrito/carga na partida; é hipótese plausível, não diagnóstico comprovado. A mensagem do programa não mede a saída do driver nem o eixo.

Criado [Teste motor 4](teste-motor-4-partida/teste-motor-4-partida.ino) com `SPEED_PERCENT=100`, preservando todas as condições de leitura, calibração, frenagem, pausa de 5 s e retomada do Teste 3. A mensagem de acionamento agora imprime o valor configurado, em vez de texto fixo de 30%.

**Antes do ensaio:** confirmar VM regulado em 5 V adequado ao motor e divisor no ECHO. Não aplicar 100% do conjunto de 8–8,4 V ao motor informado como 5 V. O usuário confirmou em seguida que VM continua ligado diretamente à bateria de 8–8,4 V. Não energizar o Teste motor 4 nessa condição com motor informado como 5 V. Adequar a alimentação antes do ensaio.

Gravar com alimentação do motor desconectada, calibrar com `c` e iniciar com `g`. Maior acionamento pode aumentar a velocidade e a distância de parada; retestar posicionamento com supervisão. Se continuar sem giro, medir VM sob comando e tensão entre A1/A2 durante acionamento, além de STBY/PWMA em relação ao GND, antes de atribuir a causa ao sensor ou motor. Interromper o comando com `p` se o motor permanecer travado.

Verificação: alterações conferidas no arquivo; sem compilador Arduino disponível e sem validação física. Não registrar como resolvido até o usuário confirmar o giro e a parada.

## Teste motor 5: autorização por sessão e ciclo contínuo — 07/11/2026

Arquivo atual para ensaio: [teste-motor-5-ciclo.ino](teste-motor-5-ciclo/teste-motor-5-ciclo.ino).

Solicitação: autorizar somente uma vez após ligar/reiniciar o ESP32 e repetir continuamente os ciclos de passagem de peças. O Teste 4 cancelava a retomada em falhas transitórias de leitura; isso exigia enviar `g` novamente. A versão 5 separa autorização da sessão do estado momentâneo do motor.

### Como operar

1. Antes de energizar: adequar VM ao motor de 5 V e instalar/confirmar o divisor no ECHO. A última confirmação ainda era bateria de 8–8,4 V diretamente no VM; código não corrige isso.
2. Gravar o Teste 5 com alimentação do motor desconectada. Monitor Serial: 115200 baud.
3. Com sensor fixo e esteira vazia, enviar `c` e aguardar a calibração e área livre estável.
4. Enviar `g` uma vez: autoriza esta sessão e inicia o motor.
5. Peça detectada: frear, aguardar pelo menos 5 segundos desde a parada e retomar automaticamente somente depois de oito leituras livres consecutivas (aproximadamente meio segundo).
6. Repetir sem novos comandos. `p` para e cancela a autorização; depois exige novo `g`. Reiniciar/desligar a placa elimina autorização e calibração, exigindo `c` e `g` novamente.

### Falhas e limites do teste

- Leitura inválida ou fundo fora da faixa param imediatamente o comando do motor. A autorização da sessão permanece, mas o movimento só retorna após a pausa mínima e oito leituras recentes de área livre dentro da faixa calibrada. Falha persistente mantém a parada.
- `p`, comando desconhecido, recalibração aceita e falha na escrita do PWM cancelam a autorização. Calibração é recusada durante movimento ou frenagem.
- A peça precisa sair da região detectada para liberar. Se ela estiver parada sobre a esteira e continuar ocupando o sensor, este teste não a expulsa sozinho: permanece parado. A saída controlada que movimenta uma peça aprovada ainda no sensor pertence à integração posterior.
- PWM permanece em 100% como no Teste 4. Pinagem, limites de distância e frenagem de 300 ms permanecem iguais. Não garante distância de parada nem detecção de toda peça pequena.
- O retorno automático após recuperação do sensor é comportamento do ensaio de bancada solicitado, que deve ser supervisionado. No sistema final com câmera/VPS, análise pendente, falha de comunicação e ausência de aprovação não podem liberar uma peça por temporização.

### Verificação desta entrega

Arquivo revisado: autorização começa falsa; partida exige calibração, leituras livres recentes e PWM disponível; detecção conserva autorização; retomada exige 5 s e oito leituras livres; `p` cancela; calibração/autorizações não são gravadas em memória persistente. Compilador Arduino não disponível: sem compilação, simulação executável ou validação física desta versão. Testes anteriores preservados.

## Repositórios GitHub — 08/11/2026

- Destino da versão atual, informado pelo usuário: [RonaldinDuCaus/EsteiraV2](https://github.com/RonaldinDuCaus/EsteiraV2).
- Referência da primeira versão: [RonaldinDuCaus/Esteira](https://github.com/RonaldinDuCaus/Esteira).
- A listagem do repositório antigo contém README.md, esp32cam_dashboard_capture.ino, esteira_api.ino e root_ca.h. Esses arquivos ainda não foram revisados nem incorporados aos testes novos. A listagem não contém código de backend/dashboard.
- Na consulta desta data, EsteiraV2 estava vazio e público. Em 08/11/2026, o usuário confirmou que deseja mantê-lo público, substituindo a preferência inicial por privado. Visibilidade pública definida pelo usuário. Autenticação da conta proprietária disponível pelo Git local.
- O plugin GitHub permanece conectado à conta sem escrita, mas foi localizada autenticação Git local como RonaldinDuCaus. O primeiro envio foi concluído pelo Git local ao destino EsteiraV2, preservando o repositório antigo.
- Arquivos locais preparados: testes 1 a 5, README, .gitignore e .gitattributes. Preservar o repositório antigo como referência e não copiar credenciais para o novo.

## Primeiro envio concluído — 08/11/2026

Publicado em `main`: [commit inicial f71d663](https://github.com/RonaldinDuCaus/EsteiraV2/commit/f71d663), contendo cinco sketches, README, .gitignore e .gitattributes. A pasta local acompanha `origin/main`. Verificação textual de padrões comuns de credenciais não encontrou ocorrências nos arquivos selecionados; isso não substitui uma auditoria de segurança. Nenhum código do repositório antigo foi copiado. Firmware permanece sem compilação local e sem validação física adicional.

## Importação do site e separação das conexões — Versão 2 — 08/11/2026

A pedido do usuário, extraído `MiniFabrica_Grupo1_Etapa1.zip` em [versao-2/site](versao-2/site/README.md). A pasta [conexoes-esp32](versao-2/conexoes-esp32/README.md) reúne o contrato real, autenticação, campos e exemplos HTTP das rotas de foto/evento. O backend original permanece junto ao site para preservar seus caminhos e dependências. Não há firmware de placas no ZIP; o motor da Versão 1 foi copiado para completar o conjunto sem mudanças.

O pacote não inclui reconhecimento por IA, controle remoto da esteira ou telemetria de dispositivos: capturas ficam pending. Origem e hashes em [ORIGEM.json](versao-2/ORIGEM.json). Foram conferidos hashes, sintaxe JavaScript e referências locais; backend, banco, VPS e hardware não foram executados. Nenhum segredo real localizado no material inspecionado; exemplos de configuração preservados.

## Versão 3 — integração solicitada — 08/11/2026

Criados firmware da esteira e da ESP32-CAM AI Thinker/OV2640, API de eventos/comandos/capturas e worker YOLOv8 separado. A dashboard tem Calibrar, Iniciar e Parar, com pedido e confirmação distintos e atualização periódica. Resultado válido do mesmo evento/boot libera uma saída controlada; desconhecido/falha mantêm parada. O antigo temporizador de cinco segundos não autoriza mais movimento.

[README da Versão 3](versao-3/README.md) e [evidências de validação](versao-3/VALIDACAO.md): 27 testes Python (12 com PostgreSQL real local), dois scripts de testes UI, sintaxe e compilação dos dois firmwares aprovados. Inferência real depende de pesos treinados e não foi validada; não houve implantação na VPS, gravação de placas ou ensaio físico. Pendências elétricas anteriores permanecem.

A configuração final exige Wi-Fi, domínio HTTPS/CA, tokens individuais e o arquivo best.pt de detecção YOLOv8 com mapa classes.json para IDs ativos do catálogo. Cadastrar fotos não treina automaticamente esse modelo. Próxima entrega de código será a Versão 4.

## Histórico

| Etapa | Resultado |
|---|---|
| OV7670 com ESP32 | Inicialização falhou com timeout SCCB/I2C e ESP_ERR_NOT_SUPPORTED; causa não determinada |
| Diagnóstico separado da OV7670 | Preparado na pasta anterior; não há resultado confirmado. Teste da câmera adiado, sem declarar defeito |
| Motor com comandos seriais | Preparado; não é a referência atual |
| Motor automático, 5 s ligado / 5 s desligado | Usuário confirmou que girou e parou corretamente; base preservada como Teste motor 1 |
| Escolha da detecção | Laser e cor avaliados e adiados; agora priorizado ultrassônico, ainda não validado |
| Organização do projeto | Pasta própria em Documentos, fora de Site, e criação deste README |

## Validação e atualização deste registro

- **Implementado:** teste automático do motor, documentação das ligações e novo teste integrado do ultrassônico com calibração e parada travada.
- **Testado fisicamente:** alternância do motor, conforme relato do usuário.
- **Não realizado pelo assistente:** compilação local e ensaio físico.
- **Pendente:** adequação elétrica, identificação do ultrassônico, divisor do ECHO, ensaio da calibração e do firmware integrado, validação da frenagem, emergência física, câmera e integração com a VPS.

A cada alteração neste projeto, atualizar este README com a data, arquivos criados/modificados, ligações efetivas, resultado do ensaio e próxima pendência. Separar sempre proposta, implementação e resultado confirmado. Preservar o último teste funcional e não declarar validado o que ainda não foi ensaiado.
