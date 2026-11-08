# API integrada — Versão 4

O protocolo atual, incluindo pedidos, reserva, upload, falhas e autenticação, está em [conexoes-esp32/README.md](../../conexoes-esp32/README.md).

O POST legado /api/v1/captures retorna 410. Use o firmware [ESP32-CAM V4](../../camera/README.md), que envia fotos vinculadas ao pedido correto. A URL é `https://minifabrica.kronux.com.br`; o token local deve corresponder a CAMERA_API_TOKEN do servidor, diferente do token do motor.
