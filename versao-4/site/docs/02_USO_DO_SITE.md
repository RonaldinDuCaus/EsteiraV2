# Uso da dashboard — Versão 4

1. Abrir `https://minifabrica.kronux.com.br/painel` e entrar com usuário e senha administrativos configurados no `.env`. A home em `/` é pública.
2. Cadastrar os componentes e fotos. Isso mantém o catálogo; o treino do detector YOLOv8 é externo ao cadastro.
3. Associar classes treinadas aos IDs do catálogo em models/classes.json e reiniciar o worker com motor parado.
4. Confirmar ESP32, ESP32-CAM e YOLO prontos. Retirar peças e clicar Calibrar; aguardar comando aplicado e leituras livres.
5. Clicar Iniciar uma vez. Cada peça detectada ficará parada até análise do evento correspondente; reconhecida/aprovada recebe saída controlada, depois o ciclo continua.
6. Parar cancela a autorização. O botão do site não substitui emergência física independente.

Desconhecido/erro: Parar, remover a peça, Calibrar e Iniciar novamente. Não usar Iniciar para aprovar uma análise pendente. Reinício da placa exige nova autorização.

Pedido aceito pelo servidor não é comando confirmado pela placa. O painel mostra cada etapa e consulta a cada 2 s sem recarregar a página. Pontuação YOLO não é garantia de acerto; motor reportado é saída GPIO, não encoder.
