# Protocolo integrado — Versão 3

Todas as operações passam pela API da VPS; as placas iniciam as conexões. A dashboard não precisa ficar aberta durante a produção.

## Autenticação

- Administrador: login existente, cookie de sessão, operações de controle protegidas e checagem de Origin quando presente.
- Motor: `Authorization: Bearer <MOTOR_API_TOKEN>`.
- Câmera: `Authorization: Bearer <CAMERA_API_TOKEN>`, diferente do token do motor.
- Cada token corresponde ao dispositivo configurado em `MOTOR_DEVICE_ID`/`CAMERA_DEVICE_ID`. Trocar esses IDs requer revisar o histórico/pareamento, com a esteira parada.
- HTTPS e certificado CA nas placas. HTTP sem TLS somente quando habilitado explicitamente para bancada.

## Dashboard

| Operação | Método/rota |
|---|---|
| Estado e condições de controle | `GET /api/v1/factory/status` |
| Calibrar | `POST /api/v1/factory/commands` com `{"action":"calibrate"}` |
| Iniciar | Mesmo caminho com `{"action":"start"}` |
| Parar | Mesmo caminho com `{"action":"stop"}` |

Um POST aceito retorna HTTP 202 com `requested=true` e o comando; isso não prova aplicação. O comando fica `pending`, depois `applied`, `rejected`, `expired` ou `superseded`. A UI consulta a cada 2 s e mostra pedido/ACK/telemetria separadamente.

Calibrar exige sensor válido e motor parado; na primeira calibração ainda não existe uma referência para exigir `area_clear`. O operador deve esvaziar a esteira antes de clicar. Iniciar exige calibração, área livre, câmera e worker YOLO prontos. Parar revoga a autorização e impede liberação por resultado tardio.

## Sincronização do motor

`POST /api/v1/devices/motor/sync`, JSON:

```json
{
  "boot_id": "UUID-gerado-a-cada-reinicio",
  "state": "awaiting_analysis",
  "motor_on": false,
  "calibrated": true,
  "sensor_valid": true,
  "area_clear": false,
  "baseline_mm": 96.2,
  "distance_mm": 65.0,
  "event_id": "UUID-do-boot-1",
  "completed_event_id": null,
  "ack_command_id": null,
  "ack_status": null,
  "ack_reason": null,
  "firmware_version": "esteira-v3.0"
}
```

`event_id` é local da placa (boot + contador); o servidor também cria um UUID interno `event.id`. A chave dispositivo/boot/evento é única. Repetir a sincronização não cria outra peça.

A resposta contém `boot_id`, `server_time`, `authorized`, `acknowledged_command_id`, `command`, `event` e `completed_event_id`. Um comando inclui `id`, `action`, `boot_id`, `created_at`, `expires_at`. ACKs são enviados repetidamente pela placa e tratados de forma idempotente. Calibração só recebe ACK aplicado após terminar; partida só após efetivar a saída.

Um evento inclui ID interno, `event_id` local, `boot_id`, `status`, `approved`, componente, nome, score e motivo. Estados: `awaiting_capture`, `processing`, `recognized`, `unknown`, `error`, `cancelled`. Somente o evento do boot/dispositivo atual, reconhecido, não concluído, dentro do prazo e com autorização recebe `approved=true`.

Ao sair da área, o motor envia `completed_event_id` local e aguarda eco do servidor. Um evento local rejeitado ainda recebe resposta terminal; isso mantém a sincronização funcional para o operador conseguir parar/recuperar.

## Câmera

`POST /api/v1/devices/camera/poll` com `{"boot_id":"UUID-da-camera","ready":true}`. Se não estiver pronta, informar `ready=false`; nenhuma reserva deve ser consumida.

Resposta: `capture=null` ou objeto com `id`, `event_id` interno, `motor_boot_id`, `lease_token` e `expires_at`. Existe uma reserva por câmera; ela pertence à inicialização que a recebeu.

Enviar JPEG binário em `POST /api/v1/devices/camera/captures/{id}` com os cabeçalhos:

```text
Authorization: Bearer <CAMERA_API_TOKEN>
Content-Type: image/jpeg
X-Capture-Lease: <lease_token>
X-Camera-Boot-ID: <boot_id-da-camera>
```

ACK inclui `event_id` igual ao ID interno da captura. A câmera retém o mesmo JPEG em RAM até ACK/expiração e repete os mesmos bytes. Mesmo upload recebe o resultado existente; bytes diferentes para a mesma captura retornam conflito. Reinício não transforma foto velha em pedido novo.

Falha: `POST /api/v1/devices/camera/captures/{id}/failure`, JSON `{"boot_id":"...","lease_token":"...","reason":"..."}`. O evento fica em erro, sem aprovação.

## YOLO e integridade

O worker separado consulta a fila persistente PostgreSQL, reserva o trabalho e roda a inferência fora da transação/servidor HTTP. O resultado só é gravado se evento, boot, autorização e prazo ainda forem válidos. Uma classe precisa estar mapeada a componente ativo; baixa pontuação, ausência ou múltiplas detecções geram desconhecido.

As rotas legadas `POST /api/v1/events` e `POST /api/v1/captures` retornam 410: elas permitiam resultados soltos sem vínculo ao ciclo e não devem ser usadas pelos novos firmwares. Os GETs administrativos de catálogo/histórico continuam.

As contagens físicas vêm dos ciclos finalizados reconhecidos/desconhecidos no fuso `America/Sao_Paulo`; pendências/falhas não contam como peça analisada válida. Testes de reconhecimento reais ainda dependem do modelo treinado e das peças.

Documentação completa de schemas: `/api/docs` com o servidor em execução. Testes opt-in PostgreSQL: `site/tests/test_factory_postgres.py`.
