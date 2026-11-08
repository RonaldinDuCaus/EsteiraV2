# Conexões com ESP32 — Versão 2

Esta pasta separa o contrato e os exemplos de comunicação encontrados no ZIP. O servidor que atende às chamadas está em [site/backend/app/main.py](../site/backend/app/main.py). Manter backend e frontend juntos preserva os caminhos originais do programa.

**Não há firmware ESP32 nem ESP32-CAM no ZIP.** O [motor de bancada](../motor/teste-motor-5-ciclo/teste-motor-5-ciclo.ino) foi preservado da Versão 1 e usa Serial; ele ainda não faz HTTP/Wi-Fi. Esta entrega organiza o material recebido, sem implementar comunicação nova nas placas.

## Fluxo disponível

```text
ESP32-CAM ou cliente HTTP
  -> POST /api/v1/captures + Bearer + bytes da imagem
  -> API salva a fotografia e cria evento pending
  -> histórico/dashboard mostram o evento
```

O código desta Etapa 1 não contém processamento de IA para finalizar esse evento. Também não tem comandos de partida/parada ou aprovação de peças. A dashboard devolve os estados de dispositivos como `awaiting`, fixos no código; isso não confirma uma placa online.

## Endereço e autenticação

- Endereço base: o servidor onde este pacote for executado; a documentação não fornece um domínio real da instalação atual.
- Token: configurar `DEVICE_API_TOKEN` no `.env` do servidor e usar o mesmo valor no cliente.
- Cabeçalho: `Authorization: Bearer <TOKEN_DO_DISPOSITIVO>`.
- Token ausente/incorreto: HTTP 401. O token é global, não individual por placa.
- `X-Device-ID` é um rótulo fornecido pelo cliente, não prova de identidade autenticada.
- Login do site usa cookie de sessão separado e não substitui o Bearer das placas.
- Para um servidor remoto definitivo, usar HTTPS com validação do certificado. O pacote só traz orientações de proxy/HTTPS, sem configuração pronta.

## Rotas existentes

| Método e caminho | Entrada | Resultado |
|---|---|---|
| `GET /api/v1/health` | Sem autenticação | HTTP 200: `status=ok`, `service=minifabrica` |
| `POST /api/v1/captures` | Bearer, imagem binária no corpo; `X-Device-ID` opcional no código | HTTP 202: `event_id`, `status=pending`, `created_at` |
| `POST /api/v1/events` | Bearer, JSON descrito abaixo | HTTP 201: `id`, `created_at` |

Documentação interativa: `/api/docs`, quando o backend estiver executando com banco disponível.

### Captura de fotografia

Enviar os bytes da imagem diretamente, sem JSON, base64 ou multipart. Para uma foto JPEG, usar `Content-Type: image/jpeg`. O código valida os bytes com Pillow; não exige esse cabeçalho nem restringe estritamente o conteúdo a JPEG.

Exemplo de resposta:

```json
{
  "event_id": 1,
  "status": "pending",
  "created_at": "2026-11-08T12:00:00Z"
}
```

O guia original [03_API_ESP32_CAM.md](../site/docs/03_API_ESP32_CAM.md) lista `X-Device-ID` como obrigatório; a implementação aceita ausência e usa `esp32-cam` como padrão. Esta documentação distingue o comportamento do código da orientação do guia original.

### Envio de evento

Campos aceitos por `EventInput`, todos opcionais:

| Campo | Tipo | Padrão |
|---|---|---|
| `component_id` | inteiro ou null | null |
| `detected_name` | texto ou null | null |
| `confidence` | número ou null | null |
| `status` | texto | `recognized` |
| `image_filename` | texto ou null | null |
| `device_id` | texto ou null | null |

O servidor registra o resultado enviado pelo cliente; esta rota não executa reconhecimento. Um `component_id` informado precisa existir no banco. A escala/intervalo de `confidence` não tem validação específica no modelo. Não chamar esse valor de probabilidade garantida.

## Exemplos de chamadas

[requisicoes.http](requisicoes.http) contém saúde, upload e criação de evento para uso em cliente HTTP. Trocar endereço/token antes do uso e fornecer uma imagem local para o upload. Não colocar credenciais reais no arquivo versionado.

Os POSTs criam dados: executar somente contra um ambiente de teste. Reenviar uma foto ou evento cria outro registro; não há chave de idempotência neste pacote. Não enviar evento separado após a captura esperando que ambos sejam unidos automaticamente: a captura já cria seu próprio evento.

## O que falta para ligar ao motor atual

- Firmware de rede das placas e configuração de Wi-Fi/servidor.
- IDs de evento/pedido de captura e tratamento de duplicidade/reenvio.
- Telemetria real, comandos confirmados e autorização por inicialização.
- Solicitação de captura, análise, consulta de resultado e aprovação do evento correto.
- Separação entre contagem de peças físicas, testes e falhas.
- Manter a parada local enquanto captura/análise estiverem pendentes.

O temporizador de 5 segundos do motor de bancada não representa aprovação pelo servidor. A integração final precisará substituir esse fluxo pelo resultado vinculado à peça.

## Validação desta separação

Mapeamento por leitura de `main.py`, `config.py`, `database.py` e guia original. Nenhuma requisição foi enviada a uma VPS ou placa. API/banco e firmware não foram executados nesta etapa.
