# Instalação e atualização na VPS — Versão 3

## Pré-requisitos e configuração

VPS Linux com Docker/Compose, armazenamento persistente e memória disponível para PyTorch/YOLO. A configuração fornecida usa **CPU**, sem presumir GPU. Recursos e tempo real de inferência ainda devem ser medidos na VPS do usuário.

Na pasta `versao-3/site`, copiar `.env.example` para `.env` e preencher:

- `POSTGRES_PASSWORD`, `ADMIN_PASSWORD`, `SESSION_SECRET`: valores fortes exclusivos.
- `MOTOR_API_TOKEN` e `CAMERA_API_TOKEN`: tokens diferentes, longos e aleatórios. Gerar localmente com `python -c "import secrets; print(secrets.token_urlsafe(32))"`, sem publicar o resultado.
- `PUBLIC_BASE_URL`: origem exata do painel, por exemplo `https://seu-dominio`, sem barra final ou caminho. Isso permite validar os comandos atrás do proxy HTTPS sem confiar em cabeçalhos arbitrários.
- `ADMIN_USERNAME`: login inicial desejado. Se o usuário já existir, o seed não altera sua senha; manter a credencial existente na atualização.
- `YOLO_CONFIDENCE`: 0,80 é apenas ponto inicial de avaliação.

Se a senha do PostgreSQL tiver caracteres reservados de URL, usar codificação adequada em `DATABASE_URL` ou gerar senha sem esses caracteres. Guardar `.env` fora do Git.

Colocar `best.pt` e `classes.json` reais em `site/models/`. Os nomes de classe precisam corresponder ao detector treinado; IDs são os do catálogo da dashboard. Consultar [guia YOLO](../models/README.md). Somente pesos confiáveis devem ser carregados.

## Nova instalação

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 app worker
```

O build do worker baixa o runtime CPU PyTorch; pode consumir tempo, rede e disco. A API permanece sem esse runtime pesado. Sem o modelo/mapa, o worker publica erro e o início da esteira fica bloqueado.

A porta da aplicação fica vinculada a `127.0.0.1:8000`. Usar o proxy HTTPS da VPS para acesso externo. Não expor o PostgreSQL. Configurar encaminhamento de cabeçalhos do proxy para o backend e manter `COOKIE_SECURE=true` em HTTPS. A verificação de Origin usa PUBLIC_BASE_URL quando configurado; o proxy deve preservar Host e encaminhar o esquema corretamente. Sem essa variável, a comparação usa a origem percebida pelo backend.

Para teste local HTTP somente em máquina/rede de bancada, ajustar `COOKIE_SECURE=false` e `PUBLIC_BASE_URL=http://localhost:8000` (ou o endereço exato de bancada), usar acesso local e habilitar explicitamente HTTP nas configurações das placas. Não usar esse modo na internet pública.

## Atualização preservando a instalação existente

1. Parar a operação pelo painel e garantir motor desabilitado. Fazer backup antes de trocar o servidor.
2. Anotar **o nome do projeto Compose e os volumes existentes**. Usar o mesmo nome ao iniciar a versão nova; caso contrário o Docker pode criar outro banco vazio, dando aparência de perda de dados.
3. Fazer backup do PostgreSQL a partir da instalação antiga:

```bash
docker compose exec -T db pg_dump -U minifabrica minifabrica > backup-antes-v3.sql
```

4. Fazer também cópia do volume de uploads e do `.env` por procedimento administrativo da VPS; o dump do banco não contém as fotografias.
5. Parar os serviços antigos sem remover os volumes. **Não usar `down -v`.**
6. Copiar a Versão 3, manter credenciais e nome do projeto antigo, acrescentar os novos tokens/modelo e executar:

```bash
docker compose --project-name NOME_DO_PROJETO_EXISTENTE up -d --build
```

7. Verificar logs, catálogo e fotos. A migração `003_factory_protocol.sql` é aplicada uma vez e preserva os dados anteriores.
8. Atualizar os dois firmwares, verificar a dashboard e executar os testes físicos supervisionados antes de produzir peças.

Não executar `scripts/reset_database.py` para instalar ou atualizar; é um utilitário destrutivo da Etapa 1.

## Backup e restauração

Manter juntos dump SQL, cópia do volume de uploads, `.env` seguro, pesos/mapa e a versão do código. Ensaiar restauração em banco separado: restaurar o dump, os uploads e as configurações antes de apontar o serviço para essa instalação. Não sobrescrever a instalação ativa para testar recuperação.

## Checklist inicial

- Login e imagens acessíveis apenas após autenticação.
- Motor/câmera online com versões e boot identificados; comandos ainda desautorizados.
- Calibração confirmada pela placa, não apenas solicitada no navegador.
- Worker pronto com modelo e classes reais.
- Ao detectar, motor parado durante captura e análise.
- Desconhecido, falha da câmera, internet perdida e análise lenta não liberam motor.
- Resultado de outra peça/boot e upload duplicado não liberam nem contam novamente.
- Após reconhecimento, saída limitada a 3 s confirma área livre e continua o próximo ciclo.
- Reinício e reconexão não dão partida automática.

Não houve acesso nem implantação na VPS nesta entrega.
