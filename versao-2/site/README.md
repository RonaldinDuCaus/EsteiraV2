# Site — Versão 2

Pacote extraído de `MiniFabrica_Grupo1_Etapa1.zip`, mantendo frontend, backend, banco, configurações e utilitários nos caminhos esperados pelo programa. O [README original](README_ORIGINAL.md) e os [guias originais](docs/) foram preservados como referência do ZIP.

## Arquivos principais

| Parte | Arquivos |
|---|---|
| Interface | [frontend/index.html](frontend/index.html), [app.js](frontend/assets/app.js), [styles.css](frontend/assets/styles.css) |
| Servidor e API | [backend/app/main.py](backend/app/main.py) |
| Configuração | [backend/app/config.py](backend/app/config.py), [.env.example](.env.example) |
| Banco | [backend/app/database.py](backend/app/database.py), [database/schema.sql](database/schema.sql) |
| Instalação | [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), [requirements.txt](requirements.txt) |
| Conexão das placas | [Documentação separada](../conexoes-esp32/README.md) e [exemplos HTTP](../conexoes-esp32/requisicoes.http) |

## Funcionalidade encontrada no código

Login e sessão administrativa, painel, cadastro de componentes com 1–10 imagens, listagem, ativação/inativação e histórico. A API serve o site no mesmo domínio e protege o acesso às imagens pela sessão do usuário.

Este ZIP é a Etapa 1: não há reconhecimento por IA implementado. O upload da câmera cria um evento `pending`. Também não há controle remoto da esteira, polling de pedidos da câmera ou telemetria real das placas. Isso pode diferir do sistema mais recente que o usuário informou já estar na VPS; esta extração não comprova que os dois sejam iguais.

## Execução prevista do site com dados reais

Requer Docker Engine/Compose e acesso para obter as imagens/dependências declaradas no pacote. Na pasta `versao-2/site/`:

1. Copiar `.env.example` para `.env` local.
2. Preencher senhas e segredos de `POSTGRES_PASSWORD`, `ADMIN_PASSWORD`, `SESSION_SECRET` e `DEVICE_API_TOKEN`; manter `ADMIN_USERNAME` conforme desejado. Não versionar `.env`.
3. Executar `docker compose up -d --build`.
4. Acessar `http://localhost:8000` em teste local ou o endereço da VPS de teste.
5. Entrar com as credenciais configuradas. Documentação da API em `/api/docs`.

O Compose prevê PostgreSQL 16 e volumes persistentes para banco e uploads. Não remover esses volumes para atualizar. O pacote não foi iniciado nem instalado por esta separação; compatibilidade das versões de dependências ainda não foi validada. O guia [01_INSTALACAO_VPS.md](docs/01_INSTALACAO_VPS.md) continua útil, mas a pasta desta entrega é `versao-2/site/`, não o nome da pasta original do ZIP.

Para exposição definitiva, a documentação original pede domínio, HTTPS, proxy e ajuste de `COOKIE_SECURE`; esses recursos não vêm configurados neste pacote. O script `reset_database.py` apaga dados e não é parte da inicialização normal.

## Prévia da interface

O comando `npm run dev` do pacote usa `scripts/preview-server.mjs` para uma prévia com dados demonstrativos (`?preview=1`), sem banco/API de produção. O script usa um caminho de URL diretamente como caminho de disco; a execução da prévia no Windows pode exigir adaptação. Ele foi preservado sem alterações nesta entrega.

`npm run check` verifica apenas a sintaxe de `frontend/assets/app.js`; não comprova funcionamento do backend, login ou integração com placas.

## Limites da separação

A implementação da conexão ESP32 permanece neste backend porque compartilha armazenamento e banco com o site. A pasta `conexoes-esp32/` reúne o contrato e exemplos para as placas; não é outro servidor e não contém firmware inventado. O conteúdo do ZIP foi mantido byte a byte, exceto o nome do README original. Mudanças futuras de código devem entrar na próxima versão do projeto.
