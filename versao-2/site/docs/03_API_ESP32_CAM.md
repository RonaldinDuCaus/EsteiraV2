# API para ESP32-CAM

## Endereço de teste

```text
POST /api/v1/captures
```

## Cabeçalhos obrigatórios

```text
Authorization: Bearer TOKEN_DO_DISPOSITIVO
Content-Type: image/jpeg
X-Device-ID: esp32-cam-01
```

O corpo da requisição deve conter diretamente os bytes da imagem JPEG.

## Resposta

```json
{
  "event_id": 1,
  "status": "pending",
  "created_at": "2026-09-22T12:00:00Z"
}
```

Nesta primeira etapa a captura fica como `pending`. A próxima etapa conectará esse evento ao serviço de reconhecimento por similaridade visual.

