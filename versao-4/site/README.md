# Mini Fábrica Kronux — Site e API, Versão 4

Domínio previsto: **https://minifabrica.kronux.com.br**. Esta entrega contém a nova página pública, o painel de operação e a API organizada por módulos. O código foi preparado localmente; a implantação na VPS ainda não foi realizada.

## Páginas e acesso

| Endereço | Conteúdo e acesso |
|---|---|
| `/` | Homepage pública do projeto: módulos, fluxo e acesso ao painel. Sem telemetria, dados de produção ou comandos reais |
| `/painel` | Página de login e painel. O HTML pode ser aberto publicamente; dados e operações exigem sessão administrativa válida |
| `/api/v1/public/info` | Nome, descrição, origem pública e caminho do painel; não expõe segredos ou telemetria |
| `/api/v1/health` | Estado básico do serviço e versão |
| `/api/docs` | Documentação dos contratos. As operações protegidas continuam exigindo sua autenticação |

O painel mantém catálogo, cadastro de referências, histórico e os comandos **Calibrar**, **Iniciar** e **Parar**. Atualiza o estado periodicamente, distingue pedido de comando da confirmação da placa e mostra a saída GPIO reportada, sem afirmar que a rotação foi medida.

## Módulos internos

Os módulos são partes deste site e da API; não são plugins de terceiros.

| Parte | Código |
|---|---|
| Homepage e painel | [frontend/index.html](frontend/index.html), [frontend/painel.html](frontend/painel.html) |
| Estilo, interface operacional e bloqueios | [styles.css](frontend/assets/styles.css), [app.js](frontend/assets/app.js), [factory-ui.js](frontend/assets/factory-ui.js) |
| Composição do servidor | [backend/app/main.py](backend/app/main.py) |
| Páginas, autenticação, catálogo, imagens e estado | [backend/app/modules](backend/app/modules/README.md) |
| Comandos, eventos e capturas das placas | [backend/app/factory.py](backend/app/factory.py) |
| Regras de aprovação | [backend/app/factory_policy.py](backend/app/factory_policy.py) |
| YOLOv8 em processo separado | [backend/app/yolo_worker.py](backend/app/yolo_worker.py) |
| Migração aditiva do protocolo | [database/migrations/003_factory_protocol.sql](database/migrations/003_factory_protocol.sql) |
| Configuração de exemplo | [.env.example](.env.example) |
| API e worker CPU | [Dockerfile](Dockerfile), [Dockerfile.worker](Dockerfile.worker), [docker-compose.yml](docker-compose.yml) |

## APIs e ligação com as ESP32

As rotas operacionais da integração continuam disponíveis. As credenciais são novas e distintas para motor e câmera; devem ser configuradas localmente nos dois lados, sem entrar no GitHub público.

| Grupo | Rotas principais | Autenticação |
|---|---|---|
| Administração | `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me` | Login e cookie de sessão |
| Catálogo e histórico | `/api/v1/components`, `GET /api/v1/events` | Sessão administrativa |
| Dashboard e módulos | `/api/v1/dashboard`, `/api/v1/system/modules`, `/api/v1/recognition/status` | Sessão administrativa |
| Controle | `GET /api/v1/factory/status`, `POST /api/v1/factory/commands` | Sessão administrativa |
| ESP32 da esteira | `POST /api/v1/devices/motor/sync` | Bearer exclusivo do motor |
| ESP32-CAM | `POST /api/v1/devices/camera/poll`, envio/falha de `/api/v1/devices/camera/captures/{id}` | Bearer exclusivo da câmera e reserva vinculada à captura |

O contrato detalhado está em [conexoes-esp32](../conexoes-esp32/README.md). Os POSTs antigos de eventos/capturas sem vínculo retornam 410; não devem ser usados pelos novos firmwares.

A esteira inicia desautorizada após reinício. O operador calibra e inicia pelo painel; peça detectada gera evento e pedido de fotografia. O motor aguarda o resultado desse evento. Reconhecimento válido permite saída controlada; desconhecido, erro ou perda de comunicação mantêm a parada. O antigo temporizador de cinco segundos não aprova peças. Recuperação e ensaios são descritos nos [firmwares do motor](../motor/README.md) e da [câmera](../camera/README.md).

## Nova instalação prevista

Seguir [o procedimento completo da VPS](docs/01_INSTALACAO_VPS.md). A configuração padrão desta versão usa uma **instância separada**, com projeto Compose `minifabrica-v4`, novos volumes e aplicação exposta apenas em `127.0.0.1:8004`. A intenção é preparar e testar sem substituir a instalação anterior.

O `.env` local contém senhas e tokens reais quando preparado pelo operador; ele é ignorado pelo Git. Não sobrescrever um `.env` já preparado copiando o exemplo por cima. `.env.example` contém apenas exemplos e não habilita produção sem configuração.

A origem pública deve permanecer `PUBLIC_BASE_URL=https://minifabrica.kronux.com.br` e os cookies em HTTPS usam `COOKIE_SECURE=true`. A verificação externa realizada durante a preparação encontrou **RemoteCertificateNameMismatch** no domínio. O certificado precisa ser corrigido para esse nome antes de usar o painel ou configurar a validação TLS das ESP32. Não desabilitar a validação para contornar esse erro.

Há duas alternativas de HTTPS: usar o proxy Nginx existente com [deploy/nginx.conf.example](deploy/nginx.conf.example), ou usar [compose.https.yml](compose.https.yml) com [Caddyfile](deploy/Caddyfile) quando as portas 80/443 estiverem disponíveis. Escolher uma; não executar ambos disputando essas portas.

## Modelo de reconhecimento

Ainda são necessários `models/best.pt` treinado para as peças e `models/classes.json` relacionando cada classe ao ID de um componente ativo. Não há pesos treinados fornecidos. O cadastro de fotos não treina automaticamente o YOLOv8.

Sem modelo/mapa válido, o worker informa a pendência e o início da esteira fica bloqueado. Ausência ou múltiplas detecções, classe sem componente ativo e pontuação baixa não aprovam a peça. A pontuação YOLO não é uma probabilidade garantida. O limiar inicial 0,80 e o desempenho da VPS CPU precisam de avaliação com imagens reais; recursos e tempo de inferência ainda não estão confirmados. Ler [models/README.md](models/README.md), incluindo as referências de treinamento e licença.

## Prévia e testes

`npm run dev` serve a apresentação em `/` e a prévia visual em `/painel?preview=1`. A prévia usa dados demonstrativos e desabilita comandos; não comprova comunicação com placas, banco ou VPS.

```text
python -m pip install -r requirements-dev.txt
python -m pytest tests
node frontend/tests/factory-ui.test.cjs
node frontend/tests/app.test.cjs
node frontend/tests/pages.test.cjs
```

Para a suíte real PostgreSQL, `FACTORY_TEST_DATABASE_URL` deve apontar exclusivamente para um banco descartável cujo nome termine em `_test`. Os testes limpam esse banco; nunca usar a base de operação. Sem essa variável, esses testes são pulados. Inferência controlada nos testes de fluxo não mede precisão do modelo real.

As evidências e limites desta entrega estão em [VALIDACAO.md](../VALIDACAO.md). Documentos `README_ORIGINAL.md` e da Etapa 1 são históricos. Para a estrutura atual, usar estes guias e a documentação da API.
