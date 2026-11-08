# Instalação inicial na VPS Hostinger

## Requisitos

- VPS Linux atualizada.
- Acesso por SSH com usuário administrativo.
- Docker Engine e Docker Compose Plugin.
- Domínio apontado para a VPS antes da configuração pública de HTTPS.

## 1. Preparar a pasta

Envie a pasta `MiniFabrica_Grupo1` para a VPS e entre nela pelo terminal.

## 2. Criar as configurações

Copie `.env.example` para `.env`. Troque todas as senhas e gere valores longos e aleatórios para `SESSION_SECRET` e `DEVICE_API_TOKEN`.

O servidor recusará a inicialização em modo de produção enquanto detectar senhas ou tokens de exemplo.

Mantenha `COOKIE_SECURE=false` durante o teste por endereço IP. Depois que o domínio e o HTTPS estiverem ativos, altere para `COOKIE_SECURE=true`.

Nunca envie o arquivo `.env` ao professor, ao GitHub ou a serviços públicos.

## 3. Iniciar

Execute:

```bash
docker compose up -d --build
```

Confira o estado:

```bash
docker compose ps
```

## 4. Primeiro acesso

Abra `http://IP_DA_VPS:8000` e use `ADMIN_USERNAME` e `ADMIN_PASSWORD` definidos no `.env`.

## 5. Próxima etapa de publicação

Antes de abrir o sistema publicamente, configure domínio, HTTPS e proxy reverso. Essa configuração será incluída junto com a versão final, quando o domínio do projeto estiver definido.
