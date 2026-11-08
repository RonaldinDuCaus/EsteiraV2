# Modelo YOLOv8

Coloque nesta pasta, localmente na VPS:

- `best.pt`: pesos de um **detector YOLOv8 treinado com as suas peças**.
- `classes.json`: objeto JSON associando o nome exato de cada classe do modelo ao ID de um componente ativo na dashboard. Use `classes.example.json` apenas como exemplo; os IDs 1 e 2 não são reservados nem criados automaticamente.

Exemplo: se a classe treinada se chama `modulo_rele` e o componente cadastrado tem ID 17, o mapeamento é `{"modulo_rele": 17}`. O catálogo mostra o ID interno para essa configuração. Reinicie o worker ao substituir modelo/mapa; faça isso com a esteira parada.

Cadastrar fotos na dashboard **não treina YOLOv8**. Para criar os pesos, é necessário um dataset anotado com caixas e classes, conjunto de validação separado, treinamento e avaliação com suas peças, incluindo peças desconhecidas. Consulte [treinamento oficial](https://docs.ultralytics.com/modes/train/) e [YOLOv8](https://docs.ultralytics.com/models/yolov8/).

O worker não baixa pesos genéricos automaticamente. Sem modelo, mapa válido ou componente ativo associado, nenhuma peça recebe liberação. O limiar 0,80 é somente configuração inicial de ensaio, não probabilidade garantida de acerto.

Ultralytics disponibiliza licença AGPL-3.0 e opção Enterprise; consulte a [licença oficial](https://www.ultralytics.com/license) para definir o uso e a distribuição adequados ao projeto. Esta entrega não atribui uma licença nova a arquivos anteriores.

Não há pesos treinados fornecidos nesta entrega. Os arquivos reais de modelo e `classes.json` devem ficar fora do repositório público.
