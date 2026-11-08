# Módulos internos da API — Versão 4

O `main.py` compõe os módulos abaixo. Não são plugins do ChatGPT nem dependem de serviços de terceiros para login ou comandos.

| Módulo | Responsabilidade | Rotas |
|---|---|---|
| `pages.py` | Homepage pública, shell de login e fotografias protegidas | `/`, `/painel`, `/uploads/{filename}` |
| `auth.py` | Senhas com hash, sessão assinada, usuário ativo e origem de alterações | `/api/v1/auth/*` |
| `catalog.py` | Cadastro, imagens, ativação e histórico | `/api/v1/components`, `/api/v1/events` GET |
| `status.py` | Metadados públicos, dashboard e descoberta dos módulos | `/api/v1/public/info`, `/api/v1/system/modules`, `/api/v1/dashboard`, `/api/v1/recognition/status` |
| `images.py` | Validação e armazenamento compartilhados das referências | Usado pelo catálogo e páginas |

O núcleo em `factory.py`, `factory_policy.py` e `yolo_worker.py` mantém o contrato das placas e as regras de autorização, evento, lease e resultado vinculado. As rotas `/api/v1/factory/*` e `/api/v1/devices/*` continuam compatíveis com os firmwares da integração anterior.

## Fronteiras de acesso

- Homepage e `/api/v1/public/info` não consultam telemetria nem expõem tokens/sessões.
- `/painel` entrega somente o HTML do login/painel. Dados operacionais, catálogo, imagens, reconhecimento e comandos exigem sessão válida de usuário ativo.
- Motor e câmera usam credenciais Bearer distintas. Um token de placa não substitui sessão administrativa.
- `PUBLIC_BASE_URL` é a origem pública HTTPS usada para conferir o cabeçalho `Origin` nas alterações feitas pelo navegador.
- Sem `ADMIN_PASSWORD` e `SESSION_SECRET`, nenhuma conta administrativa padrão é criada. Em produção, configurações ausentes/fracas, tokens iguais, origem sem HTTPS e cookie sem `Secure` impedem inicialização.
- Os POSTs legados `/api/v1/events` e `/api/v1/captures` retornam 410; não há rota para um cliente fabricar um reconhecimento.

Treino e pesos YOLO continuam externos ao cadastro de referências. A API não afirma que cadastrar fotografias treine um detector automaticamente.
