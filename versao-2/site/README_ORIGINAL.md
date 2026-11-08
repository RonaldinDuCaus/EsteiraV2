# Mini Fábrica Inteligente Grupo 1

Primeira versão funcional do sistema de reconhecimento de componentes eletrônicos. O projeto reúne painel web, cadastro de componentes, histórico, API para a ESP32-CAM e banco PostgreSQL.

## O que já funciona

- Login administrativo.
- Dashboard responsivo para computador e celular.
- Cadastro de componentes com uma ou várias imagens.
- Listagem e ativação ou desativação de componentes.
- Histórico de capturas e reconhecimentos.
- Endpoint protegido para a ESP32-CAM enviar fotografias.
- Armazenamento de imagens fora do banco e metadados no PostgreSQL.
- Execução por Docker Compose.

## Início rápido na VPS

1. Copie `.env.example` para `.env`.
2. Troque todas as senhas, o segredo de sessão e o token dos dispositivos.
3. Execute `docker compose up -d --build`.
4. Abra `http://IP_DA_VPS:8000`.
5. Entre com o usuário e a senha definidos em `.env`.

Leia os guias numerados na pasta `docs` antes de expor o sistema à internet.

## Estrutura

- `backend`: API FastAPI e regras do sistema.
- `frontend`: site responsivo.
- `database`: referência do esquema PostgreSQL.
- `data/uploads`: pasta usada em desenvolvimento local.
- `docs`: instalação, uso e integração.
- `scripts`: utilitários administrativos.

## Estado da IA

A etapa atual prepara o cadastro, as imagens e os eventos. O reconhecimento por similaridade visual será adicionado na próxima etapa sem alterar o fluxo principal do site.

Na instalação Docker, as imagens ficam em um volume persistente chamado `uploads_data`.
