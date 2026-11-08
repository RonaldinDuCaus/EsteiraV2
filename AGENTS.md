# Procedimento do Projeto Esteira IoT

Instrução do usuário em 08/11/2026: manter versões completas em pastas numeradas e README em cada versão.

- Antes de trabalhar, ler o README da raiz e o README da versão mais recente.
- Cada nova entrega que altere código ou configuração deve criar a próxima pasta `versao-N` (versao-1, versao-2, etc.). O número identifica o conjunto completo, não cada componente. Não criar uma versão por salvamento intermediário da mesma entrega.
- Copiar os arquivos da versão anterior para a nova, preservando as versões já entregues. Não editar sketches históricos ou versões entregues para aplicar uma correção; a correção pertence à próxima versão.
- Dentro de cada versão, organizar os componentes existentes em `motor/`, `camera/` e `site/`. Não criar módulos vazios ou declarar integração não implementada. Preservar o nome correspondente entre pasta de sketch Arduino e arquivo .ino.
- Cada versão deve ter README próprio: objetivo, origem, mudanças, arquivos, ligações, dependências, execução, configuração, testes executados, limitações e pendências. Links internos devem ser relativos e funcionar no GitHub.
- Componentes não alterados acompanham a nova versão como cópias reais. Evitar dependência em código mutável de outra versão. Quando integrações existirem, documentar contratos e compatibilidade do conjunto.
- README da raiz é índice vivo e pode ser atualizado sem duplicar versão de código. Registros de resultados do usuário podem ser acrescentados à documentação, distinguindo data da entrega e data da validação. Nunca alterar retroativamente o código entregue.
- Regras deste AGENTS.md, .gitignore e .gitattributes são metadados da raiz; mudanças nesses arquivos não exigem uma nova versão de firmware.
- Os testes 1 a 5 na raiz são histórico anterior ao procedimento. Preservá-los. Versao-1 inicia com cópia do Teste Motor 5.
- Atualizar README e GitHub EsteiraV2 ao concluir as entregas autorizadas. Repositório público por decisão do usuário. Não versionar credenciais, tokens, arquivos .env reais ou dados privados.
- Usar a conta Git local RonaldinDuCaus quando o plugin continuar conectado à outra conta. Não alterar conexões nem permissões de terceiros.
- Não declarar compilação, simulação, funcionamento físico ou precisão sem evidência. Confirmar pendências elétricas registradas nos READMEs antes de orientar energização.
