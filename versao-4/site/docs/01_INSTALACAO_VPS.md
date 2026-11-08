# Instalação e atualização na VPS — Versão 4

Destino previsto: **https://minifabrica.kronux.com.br**. A entrega prepara uma instalação nova e isolada; não houve implantação, alteração de proxy ou troca do site atualmente hospedado.

## 1. Conferir o ambiente e o certificado

Requer VPS Linux, Docker Engine/Compose, acesso administrativo e armazenamento/memória para PostgreSQL e PyTorch/YOLOv8 em CPU. GPU não foi presumida. O worker pesado fica separado da API, mas sua capacidade e tempo de inferência precisam ser medidos na VPS real.

A verificação externa da preparação encontrou `RemoteCertificateNameMismatch`: o certificado apresentado não correspondia ao domínio solicitado. Corrigir o certificado para `minifabrica.kronux.com.br` antes de operar o painel ou as ESP32 por HTTPS. As placas precisam confiar na CA adequada; não usar modo inseguro para contornar o certificado.

Verificar o apontamento DNS e identificar quem já ocupa 80/443. Usar o proxy existente ou o Caddy opcional deste pacote, conforme as alternativas abaixo. Não parar outros serviços apenas para liberar essas portas.

## 2. Preparar uma instância nova

Copiar a pasta `versao-4/site` para um diretório próprio da VPS e entrar nele. Não substituir arquivos ou `.env` da instalação antiga.

O exemplo define:

- `COMPOSE_PROJECT_NAME=minifabrica-v4`: namespace novo para containers e volumes.
- `SITE_DOMAIN=minifabrica.kronux.com.br`: domínio usado pelo Caddy opcional.
- `PUBLIC_BASE_URL=https://minifabrica.kronux.com.br`: origem exata para validar alterações administrativas.
- `APP_ENV=production` e `COOKIE_SECURE=true`.
- Porta da aplicação vinculada a **`127.0.0.1:8004`**, sem publicar PostgreSQL.

Criar `.env` a partir de `.env.example` somente se ainda não houver um arquivo real preparado. Preservar o arquivo local já gerado para esta entrega; ele não deve ser enviado ao GitHub, mostrado em logs ou compartilhado publicamente.

Preencher `POSTGRES_PASSWORD`, `ADMIN_PASSWORD`, `SESSION_SECRET`, `MOTOR_API_TOKEN` e `CAMERA_API_TOKEN` com valores fortes e exclusivos. Os tokens das placas precisam ser diferentes entre si e corresponder aos usados em suas configurações locais. Definir o usuário administrativo desejado. Não usar os marcadores do exemplo como credenciais.

A URL do PostgreSQL é montada pelo Compose. Usar uma senha forte sem caracteres reservados de URL, ou adaptar corretamente a codificação da URL; não basta inserir caracteres reservados sem tratamento. Restringir acesso ao arquivo:

```bash
chmod 600 .env
```

Os volumes padrão desta instância são associados ao projeto `minifabrica-v4`, como `minifabrica-v4_postgres_data` e `minifabrica-v4_uploads_data`. Isso cria um banco novo e não importa catálogo/fotos da instalação antiga automaticamente. Confirmar os nomes efetivos no Docker antes de qualquer migração.

## 3. Fornecer o modelo real

Colocar em `site/models/` na VPS:

- `best.pt`: detector YOLOv8 treinado para os módulos utilizados.
- `classes.json`: associação dos nomes exatos das classes aos IDs dos componentes ativos no catálogo.

Consultar [models/README.md](../models/README.md). Ambos continuam pendentes nesta entrega. O worker não baixa pesos genéricos para aprovar componentes, e cadastrar fotografias no painel não treina o detector. Sem modelo/mapa válido, o serviço mostra a pendência e não permite iniciar a esteira.

## 4. Subir o servidor interno

Na pasta `versao-4/site`:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 app worker
curl --fail http://127.0.0.1:8004/api/v1/health
```

O build do worker CPU pode consumir rede, disco e tempo. Esses comandos pressupõem a configuração preenchida e Docker disponível; não foram executados na VPS nesta entrega. A saúde básica não garante que câmera, motor ou modelo estejam prontos.

Em produção, o login precisa ser acessado pela origem HTTPS configurada, pois os cookies são `Secure`. O endereço local HTTP acima serve apenas para checar a saúde interna do servidor.

## 5. Escolher uma alternativa de HTTPS

### Alternativa A — Nginx já existente na VPS

Usar [deploy/nginx.conf.example](../deploy/nginx.conf.example) como referência, adaptando ao proxy atual sem substituir suas outras configurações. O destino da aplicação deve ser `http://127.0.0.1:8004`. O Host e o esquema original devem ser encaminhados como no exemplo.

O arquivo usa caminhos de certificado Let’s Encrypt referentes a `minifabrica.kronux.com.br`. Esses caminhos são exemplos: o certificado precisa existir, cobrir o domínio e ter cadeia válida antes de ativar esse bloco HTTPS. Se o proxy já gerencia certificados de outra forma, manter esse gerenciamento e ajustar os caminhos.

Depois de preparar o domínio/certificado e integrar a configuração ao proxy:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Não ativar `compose.https.yml` nessa alternativa. O Nginx existente continua responsável por 80/443.

### Alternativa B — Caddy do pacote, somente com 80/443 disponíveis

Usar apenas se o servidor não tiver outro proxy atendendo essas portas e se DNS/firewall permitirem a emissão do certificado para o domínio correto. `SITE_DOMAIN` deve conter `minifabrica.kronux.com.br`, sem protocolo ou caminho.

```bash
docker compose -f docker-compose.yml -f compose.https.yml up -d --build
docker compose -f docker-compose.yml -f compose.https.yml logs --tail=100 caddy
```

O Caddy atende externamente em 80/443 e encaminha para `app:8000` na rede do Compose. Seus dados de certificado ficam nos volumes `caddy_data` e `caddy_config`; preservá-los em atualizações. Não executar simultaneamente outro servidor disputando 80/443.

Após escolher uma alternativa, verificar sem ignorar TLS:

```bash
curl --fail https://minifabrica.kronux.com.br/api/v1/health
```

A homepage fica em `/` e o painel em `/painel`. Abrir o painel, fazer login e confirmar catálogo e imagens. A página pública não expõe telemetria nem controla equipamento. APIs operacionais sem sessão devem recusar o acesso; tokens de motor/câmera não substituem login administrativo.

## 6. Configurar placas e iniciar um ensaio

Usar as configurações locais dos [firmwares do motor](../../motor/README.md) e da [ESP32-CAM](../../camera/README.md). Configurar `SERVER_URL` com a origem HTTPS deste domínio, CA válida e o token exclusivo de cada dispositivo. Não misturar tokens de uma instalação anterior com os novos.

Na dashboard:

1. Aguardar telemetria recente das duas placas.
2. Retirar as peças e usar **Calibrar**; aguardar o ACK da placa.
3. Confirmar que o worker está pronto com os pesos e mapa reais.
4. Usar **Iniciar** e ensaiar uma peça de cada vez.
5. Confirmar parada durante captura/análise, identificação vinculada ao evento correto e saída controlada apenas após aprovação.

Desconhecido, falha de câmera, perda de comunicação e demora da análise não devem liberar a esteira. **Parar** revoga a autorização; reinício/reconexão não dão partida automática. As pendências elétricas e os ensaios físicos do motor/sensor continuam aplicáveis conforme o README do firmware.

## 7. Se a intenção for atualizar uma instalação existente

O procedimento padrão acima cria uma instância nova. Uma atualização que precisa aproveitar o banco e as fotos antigos exige um plano diferente:

1. Parar a operação e garantir o motor desabilitado.
2. Identificar o nome real do projeto Compose, volumes de banco/uploads, versão atual e credenciais existentes.
3. Fazer dump do banco a partir da instalação antiga e cópia do volume de fotografias. Guardar `.env`, pesos/mapa e código junto ao backup de forma segura.
4. Preservar as credenciais do PostgreSQL que inicializaram o volume. Alterar apenas `POSTGRES_PASSWORD` no `.env` não troca a senha de um banco já inicializado.
5. Preservar a senha administrativa existente: o seed cria o usuário se ele não existir, mas não rotaciona sua senha. Trocar `ADMIN_PASSWORD` no arquivo não atualiza automaticamente o hash do usuário existente.
6. Manter o mesmo nome de projeto e volumes se o objetivo for atualizar no lugar; não usar cegamente `minifabrica-v4`, pois isso pode abrir um banco novo vazio. Se a opção for migração para instância isolada, restaurar banco e uploads nessa nova instância antes de mudar o proxy.
7. Aplicar as migrações aditivas e conferir catálogo, fotos e histórico antes de liberar a operação. A migração `003_factory_protocol.sql` não deve apagar os dados anteriores.
8. Atualizar tokens/configurações das duas placas de forma coordenada, com o motor parado. Rotacionar `SESSION_SECRET` invalida sessões; planejar novo login.

Exemplo de dump executado na pasta da instalação antiga:

```bash
docker compose exec -T db pg_dump -U minifabrica minifabrica > backup-antes-v4.sql
```

Não executar `docker compose down -v`, não apagar volumes e não usar `scripts/reset_database.py` para instalar ou atualizar. Esses procedimentos podem destruir dados. O dump não contém os arquivos de imagem: o backup dos uploads também é necessário.

## Backup e limites da entrega

Ensaiar restauração em ambiente separado com dump SQL, uploads, configurações, pesos/mapa e a versão de código correspondente. Não usar a instalação ativa para testar recuperação.

Foram preparados código e arquivos de implantação; não houve acesso SSH, implantação ou alteração do certificado/proxy da VPS nesta entrega. `best.pt`, `classes.json`, capacidade da VPS e validação física continuam pendentes. Ver [VALIDACAO.md](../../VALIDACAO.md) para as verificações realizadas localmente.
