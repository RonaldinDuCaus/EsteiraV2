# Versão 4 — novo site, módulos e credenciais

Entrega de 08/11/2026, baseada na Versão 3. Domínio configurado: **https://minifabrica.kronux.com.br**. Esta pasta contém o conjunto completo, sem depender de arquivos de outra versão.

## O que mudou

- Nova home pública em `/`, com apresentação do projeto e fluxo sensor → câmera → YOLOv8 → liberação.
- Painel de operação em `/painel`, com login, catálogo, histórico e botões **Calibrar**, **Iniciar** e **Parar**.
- API organizada em módulos do próprio site: acesso, catálogo, histórico, imagens, controle e reconhecimento. Não é um plugin do ChatGPT.
- Novos endpoints de informações públicas e estado dos módulos; controles, imagens e dados administrativos continuam autenticados.
- Novas credenciais independentes para câmera, motor, sessão, administrador e PostgreSQL, geradas localmente e excluídas do Git. Os tokens das placas já estão sincronizados nos `config.h` privados.
- Novos sketches V4 com domínio preenchido e bundle público de certificados do Arduino-ESP32. Uma CA personalizada continua opcional.
- Instância Docker identificada por `minifabrica-v4`, aplicação em `127.0.0.1:8004` e exemplos de HTTPS com Nginx existente ou Caddy.

O protocolo de produção da V3 foi preservado: a esteira só libera a peça mediante reconhecimento aprovado do mesmo evento e inicialização. O temporizador de cinco segundos não autoriza mais movimento.

## Arquivos atuais

| Parte | Código e documentação |
|---|---|
| Esteira / ESP32 | [esteira-v4.ino](motor/esteira-v4/esteira-v4.ino), [config.example.h](motor/esteira-v4/config.example.h), [ligações e operação](motor/README.md) |
| ESP32-CAM AI Thinker / OV2640 | [esp32cam-v4.ino](camera/esp32cam-v4/esp32cam-v4.ino), [config.example.h](camera/esp32cam-v4/config.example.h), [guia da câmera](camera/README.md) |
| Site, API e worker | [guia do site](site/README.md), [home](site/frontend/index.html), [painel](site/frontend/painel.html), [módulos da API](site/backend/app/modules/README.md) |
| Comunicação | [protocolo ESP32](conexoes-esp32/README.md) |
| Publicação | [instalação na VPS e HTTPS](site/docs/01_INSTALACAO_VPS.md) |
| IA | [modelo e mapa de classes](site/models/README.md) |
| Evidências | [VALIDACAO.md](VALIDACAO.md) |

## Como funciona

1. Com a esteira vazia, o operador solicita **Calibrar** e aguarda confirmação aplicada pela placa.
2. **Iniciar** autoriza a sessão quando calibração, sensor, câmera e worker estão prontos.
3. Uma peça reduz a distância medida: o controle local freia e aguarda estabilização.
4. O servidor reserva uma captura; a câmera envia o JPEG do pedido correto.
5. O worker YOLOv8 relaciona a detecção ao catálogo ativo e registra o resultado no painel.
6. A aprovação do mesmo evento permite saída controlada, limitada a 3 s e confirmada pelo sensor. O ciclo seguinte continua automaticamente.

Desconhecido, ambiguidade, erro, sensor inválido, reinício, análise demorada ou perda de comunicação mantêm/cancelam o movimento. **Parar** revoga a autorização e impede liberação por resultado atrasado. A dashboard não precisa ficar aberta durante a operação.

## Configuração local

Na cópia local desta entrega, `site/.env` e os dois `config.h` foram preparados com novos segredos correspondentes e a rede previamente informada, sem exibir os valores. O usuário/senha administrativos estão no `.env`; as placas usam seus tokens individuais. Esses arquivos não acompanham o GitHub. Em outro computador, preencher os exemplos privados conforme os guias.

Instalar o pacote **esp32 by Espressif Systems 3.3.12** no Gerenciador de Placas e a biblioteca **ArduinoJson by Benoit Blanchon 7.4.3** no Gerenciador de Bibliotecas. `WiFi`, `HTTPClient`, `WiFiClientSecure` e `esp_camera` vêm com o pacote ESP32. Selecionar **ESP32 Dev Module** para o motor e **AI Thinker ESP32-CAM** para a câmera.

O backend requer o modelo treinado `best.pt` e `classes.json` associando classes aos IDs reais do catálogo. Cadastrar fotos não treina automaticamente o YOLO. Sem esses arquivos válidos, o worker permanece indisponível e a partida fica bloqueada.

## Estado real e pendências

- **Código:** 37 testes Python com PostgreSQL local real e três arquivos de testes Node aprovados; ambos os firmwares compilados. Home e painel conferidos no navegador, incluindo home em tela de celular.
- **Servidor:** preparado para o domínio informado, mas não implantado na VPS. A verificação HTTPS encontrou `RemoteCertificateNameMismatch`; corrigir o certificado no proxy antes de conectar as placas. O firmware mantém validação de hostname e cadeia.
- **Hardware:** sem gravação ou ensaio físico da V4. A última confirmação ainda é bateria de 8–8,4 V em motor informado como 5 V; adequar a alimentação antes do acionamento a 100%. Divisor ECHO, corrente de partida, frenagem e emergência física ainda exigem confirmação.
- **IA:** pesos treinados, mapa final, recursos da VPS, latência e precisão nas peças reais pendentes.

As versões anteriores permanecem preservadas. A próxima entrega de código/configuração será a **Versão 5**.
