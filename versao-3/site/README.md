# Site e YOLOv8 — Versão 3

Esta versão integra dashboard, ESP32 da esteira, ESP32-CAM e worker YOLOv8 através de eventos persistentes. A VPS continua sendo o servidor previsto; esta entrega não foi implantada nela.

## Início

1. Ler [instalação e atualização](docs/01_INSTALACAO_VPS.md).
2. Configurar `.env` local a partir de `.env.example` com senhas e tokens diferentes para motor/câmera.
3. Fornecer `models/best.pt` treinado e `models/classes.json`, conforme [guia do modelo](models/README.md).
4. Iniciar `db`, `app` e `worker` via Docker Compose, com volumes existentes preservados.
5. Configurar/gravar os [firmwares do motor](../motor/README.md) e da [câmera](../camera/README.md).
6. Na dashboard, aguardar dispositivos online, retirar peças, **Calibrar**, aguardar confirmação e **Iniciar**.

**Parar** revoga a autorização. Reconhecimento desconhecido ou falha mantém a parada; recuperar com Parar, remoção da peça, Calibrar e Iniciar. Não existe mais liberação do motor por aguardar cinco segundos.

## Processos e arquivos

| Parte | Local |
|---|---|
| Dashboard e controles | `frontend/index.html`, `frontend/assets/app.js`, `factory-ui.js` |
| Autenticação, catálogo, histórico | `backend/app/main.py` |
| API de comandos/eventos/captura | `backend/app/factory.py` |
| Política de aprovação | `backend/app/factory_policy.py` |
| Inferência fora da API | `backend/app/yolo_worker.py` |
| Migração aditiva | `database/migrations/003_factory_protocol.sql` |
| Dependências leves da API | `requirements.txt`, `Dockerfile` |
| Dependências do worker CPU | `requirements-yolo.txt`, `Dockerfile.worker` |
| Contrato das placas | [conexoes-esp32](../conexoes-esp32/README.md) |

A migração cria tabelas novas e registra sua aplicação em transação, com bloqueio de migração antes do DDL. Não apaga catálogo, fotografias ou eventos anteriores. `database/schema.sql` é a referência original da Etapa 1; a aplicação aplica também as migrações versionadas.

## Reconhecimento

O worker usa a biblioteca Ultralytics para carregar um detector YOLOv8 local. Não baixa pesos genéricos nem aprende automaticamente com o cadastro de fotos. Exige mapa de classes para IDs ativos do catálogo. Sem modelo/mapa, a dashboard informa o erro e Iniciar fica bloqueado. Múltiplas caixas, ausência de detecção, classe sem componente ativo ou pontuação baixa não aprovam.

A pontuação do detector não é similaridade entre fotos nem probabilidade garantida. O limiar inicial 0,80 precisa de calibração com imagens reais e desconhecidas. Arquivo treinado e recursos da VPS ainda não foram fornecidos/confirmados.

A API atende comandos e consultas enquanto o processo separado executa o modelo. Há limite de prazo por evento e verificação do boot/autorização antes de aceitar resultado. Reenvios de evento/foto não geram nova contagem. Os indicadores físicos contam apenas reconhecidos/desconhecidos no fuso America/Sao_Paulo.

## Testes

```text
python -m pip install -r requirements-dev.txt
python -m pytest tests
node --test frontend/tests/factory-ui.test.cjs frontend/tests/app.test.cjs
```

Para incluir integração real PostgreSQL, definir `FACTORY_TEST_DATABASE_URL` para um banco **descartável cujo nome termine em _test**. Essa suíte limpa as tabelas entre os ensaios e nunca deve apontar para a base da VPS real. Sem essa variável, esses testes são pulados.

A inferência é substituída por resultado controlado nos testes de fluxo; isso não testa precisão do YOLOv8. Evidências em [VALIDACAO.md](../VALIDACAO.md).

## Prévia

`npm run dev` mostra dados demonstrativos; os botões de comando ficam desabilitados. Essa prévia não se conecta a uma placa. No modo real, a interface consulta o servidor a cada 2 s e distingue comando solicitado, ACK recebido e saída GPIO reportada. Sem encoder, não mede rotação física.

`README_ORIGINAL.md` e documentos da Etapa 1 são históricos. Os guias desta versão e a API em `/api/docs` descrevem o fluxo atual. Rotas POST legadas sem vínculo ao ciclo retornam 410.
