# Versão 2 — site e conexões ESP32 separados

Data: 08/11/2026. Origem: `MiniFabrica_Grupo1_Etapa1.zip`, fornecido pelo usuário, e motor da Versão 1.

## Onde está cada parte

| Parte | Pasta / documento |
|---|---|
| Site completo: frontend, backend, banco e instalação | [site/README.md](site/README.md) |
| Conexões ESP32: contrato da API e exemplos de envio | [conexoes-esp32/README.md](conexoes-esp32/README.md) |
| Exemplos HTTP | [conexoes-esp32/requisicoes.http](conexoes-esp32/requisicoes.http) |
| Motor preservado da Versão 1 | [motor/teste-motor-5-ciclo/teste-motor-5-ciclo.ino](motor/teste-motor-5-ciclo/teste-motor-5-ciclo.ino) |
| Origem e hashes dos arquivos importados | [ORIGEM.json](ORIGEM.json) |

```text
versao-2/
├── README.md
├── ORIGEM.json
├── site/
│   ├── README.md
│   ├── README_ORIGINAL.md
│   ├── frontend/
│   ├── backend/
│   ├── database/
│   ├── docs/
│   ├── scripts/
│   ├── data/uploads/
│   ├── .env.example
│   ├── requirements.txt
│   ├── package.json
│   ├── Dockerfile
│   └── docker-compose.yml
├── conexoes-esp32/
│   ├── README.md
│   └── requisicoes.http
└── motor/
    └── teste-motor-5-ciclo/
        └── teste-motor-5-ciclo.ino
```

## O que mudou

- Importados os 26 arquivos do ZIP, preservando seus bytes e a estrutura interna necessária ao site.
- README original do ZIP renomeado para `site/README_ORIGINAL.md`; criado um README de orientação na pasta do site.
- Separados o contrato e os exemplos da conexão ESP32 em pasta própria, com referência à implementação real no backend.
- Copiado o motor da Versão 1 sem alterações. Nenhum firmware novo foi inventado e nenhuma placa foi acionada.

A API continua dentro de `site/backend/app/main.py`, pois depende do mesmo banco, armazenamento e autenticação do site. `conexoes-esp32/` documenta o lado de comunicação; não é um serviço independente. Esta entrega separa e organiza os arquivos, sem refatoração funcional do backend.

## Conexão encontrada

- `POST /api/v1/captures`: Bearer + bytes da foto; salva imagem e cria evento `pending`.
- `POST /api/v1/events`: Bearer + JSON; registra evento informado pelo cliente.
- `GET /api/v1/health`: verificação pública do servidor.

Não há firmware `.ino` no ZIP, reconhecimento por IA, comandos remotos de esteira, fila de captura nem telemetria real. O motor de bancada não tem Wi-Fi/HTTP e ainda não está integrado ao site. Isso se refere ao pacote recebido, não comprova o estado do site mais recente que o usuário informou estar na VPS.

## Como usar cada parte

Para executar o site com banco, seguir [site/README.md](site/README.md): configurar `.env` local e executar Docker Compose a partir de `site/`. Foram preservadas as dependências originais; instalação e execução ainda não foram validadas. A prévia via Node utiliza dados de demonstração e não equivale ao servidor com banco.

Para preparar a comunicação das placas, consultar [conexoes-esp32/README.md](conexoes-esp32/README.md). Os exemplos HTTP exigem endereço/token de teste e uma imagem local fornecida pelo operador. Nenhuma chamada foi feita a dispositivos ou VPS nesta separação.

Para o motor, permanecem as [ligações e instruções da Versão 1](../versao-1/README.md); o sketch nesta versão é uma cópia completa. Configuração: PWMA=25, AIN1=26, AIN2=27, STBY=33, TRIG=18, ECHO=19 via divisor. Usar `c`, depois `g`, e `p` para cancelar a sessão. Autorização por reinício, pausa mínima de 5 s e retomada com área livre estável permanecem iguais.

**Pendências do motor preservadas:** adequar alimentação do motor informado como 5 V (última confirmação: bateria de 8–8,4 V em VM), confirmar divisor do ECHO, corrente de partida, frenagem e emergência física. O sketch usa 100% de acionamento e não deve ser energizado com alimentação incompatível. Ainda não há validação física confirmada do Teste Motor 5.

## Validação realizada

- Inventário do ZIP: 26 arquivos, sem firmware de placas e sem fotografias de produção.
- Hashes SHA-256 conferidos para arquivos importados e motor preservado.
- Sintaxe de `frontend/assets/app.js` e `scripts/preview-server.mjs` verificada com `node --check`.
- Referências locais da documentação nova conferidas.
- Mapeamento estático de rotas, campos e autenticação feito no código fonte.

Não foram executados backend/PostgreSQL/Docker, instalação de dependências, reconhecimento de imagens, gravação de firmware ou ensaio físico. Não foi feita implantação na VPS. Os valores de credenciais presentes no ZIP são exemplos; nenhum `.env` real veio no pacote. Manter credenciais reais fora do repositório público.

## Próximos passos

Identificar a versão efetivamente instalada na VPS e o firmware da câmera disponível antes de adaptar o fluxo. Integrar IDs de captura/evento, confirmação de comando, resultado de análise e saída controlada em uma próxima versão. O temporizador do ensaio do motor não deve servir como aprovação de peça no sistema final.
