# Last War — presenças e equipes

Aplicação local para conferir rankings e montar equipes para Tempestade do Deserto e Guerra do Canyon. Usa Python/FastAPI, Tesseract e uma interface HTML/JavaScript sem compilação. Não acessa o jogo. Os dados ficam no navegador deste computador; o servidor processa as imagens localmente.

## Instalação e execução no Windows

1. Instale Python 3.10–3.12 em <https://www.python.org/downloads/> e habilite o launcher `py`.
2. Instale o [Tesseract OCR para Windows](https://github.com/UB-Mannheim/tesseract/wiki), incluindo o idioma inglês. O caminho padrão `C:\Program Files\Tesseract-OCR\tesseract.exe` é detectado automaticamente. Para outro caminho, adicione-o ao PATH ou defina `TESSERACT_CMD` com o caminho completo do executável.
3. Abra `iniciar.bat` com dois cliques. Na primeira execução serão instaladas as dependências; é necessária conexão nessa etapa. Acesse <http://127.0.0.1:8000> e mantenha a janela do servidor aberta.

Alternativa no PowerShell, dentro da pasta do projeto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Presenças

1. Escolha o evento e a data. Cadastre jogadores pelo campo acima da lista ou use **Importar lista / CSV** para importar um CSV UTF-8 com coluna `nome`. O exemplo em `exemplos/convocados.csv` contém dados fictícios. Listas cadastradas na versão anterior são importadas ao abrir a nova interface no mesmo navegador.
2. Clique na área de prints para selecionar arquivos ou arraste um ou mais PNG/JPEG de até 20 MB cada para o visualizador. Também é possível usar **Adicionar prints**. Em **Configurar regiões de leitura**, ajuste para cada evento o início e fim da coluna de nomes e da coluna de pontos, em porcentagem da largura. Mantenha nível, poder e posição fora dessas regiões. Os valores padrão são apenas um ponto de partida e devem ser calibrados com os prints do jogo.
3. Clique em **Analisar prints**. Pontos maiores que zero resultam em **Presente**, zero em **Ausente**. Nomes não encontrados ficam **Não identificado**; números ambíguos, confiança baixa e duplicatas ficam para revisão. Nenhum valor é inferido quando a leitura falha.
4. Clique no jogador para localizar a região no print, ou na região para selecionar o jogador. Navegue pelos prints, ajuste o zoom e corrija pontos e status diretamente na lista. Leituras sem associação podem ser atribuídas manualmente abaixo da lista. Duplicatas são sinalizadas; valores conflitantes ficam vazios.
   O nome reconhecido aparece na lista. Quando um possível fragmento de avatar é removido da leitura, o jogador associado permanece em **Revisar** para confirmação. Se a leitura inicial não encontrar pontos, o OCR tenta novamente na faixa correspondente à linha. Um zero reconhecido é marcado como **Ausente**, mesmo com confiança baixa; valores positivos com baixa confiança permanecem em revisão. Confira o print e, se necessário, corrija os pontos ou o status manualmente.
5. Use **Salvar histórico**. Depois de salva, as correções dessa batalha são persistidas ao editá-la. Abra batalhas anteriores pelo histórico e use **Nova batalha** para iniciar outra. Exporte o CSV quando necessário. Ao repetir o OCR, as correções manuais são preservadas; resultados de versões anteriores sem indicação de origem são preservados por precaução.

Em **Gerenciar jogadores**, escolha um jogador e cadastre aliases separados por ponto e vírgula. O reconhecimento considera maiúsculas/minúsculas, Unicode compatível, espaços, acentos latinos e símbolos decorativos nas extremidades. Nomes aproximados são associados apenas quando há diferença suficiente para o segundo candidato e ficam em **Revisar**. Os limites de similaridade e margem podem ser ajustados nas configurações de leitura.

Os dados e o histórico ficam no `localStorage` e os prints no IndexedDB do navegador, no mesmo computador e perfil. Limpar os dados do navegador os remove; exporte os CSVs para guardar uma cópia dos resultados. Outros navegadores e computadores não compartilham esses dados.

## Montagem de equipes

Escolha o evento, ajuste os limites de titulares e reservas e use os botões de cada jogador. Também é possível cadastrar jogadores diretamente nessa tela; o cadastro é compartilhado com a tela de presenças. A sugestão automática é opcional e pede confirmação antes de substituir uma escala existente. A classificação combina frequência, quantidade de batalhas confirmadas e sequência de ausências; jogadores sem histórico suficiente recebem uma estimativa neutra. Presenças e ausências são calculadas somente com status confirmados para o evento selecionado. A tela avisa se os limites forem ultrapassados. A lista pode ser copiada ou exportada em CSV.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests\test_review.js
node tests\test_browser.mjs
```

O teste de navegador usa perfil isolado, dados fictícios, Node com WebSocket nativo e Microsoft Edge; em outro caminho, defina `EDGE_BINARY`. O teste de OCR usa imagem sintética e requer Tesseract e a fonte Arial do Windows. Os exemplos também são fictícios. O OCR utiliza colunas configuradas e associa elementos pela posição horizontal na mesma faixa vertical; nomes acima dos pontos e layouts diferentes exigem revisão manual. Calibre as regiões para cada evento e confira os resultados antes de usá-los.

Para diagnóstico local, defina `$env:LASTWAR_OCR_DEBUG='1'` antes de iniciar o servidor. O terminal exibirá nomes lidos, candidatos, pontos e motivo de revisão; desative a variável para o uso normal.

## Publicação no Render

O projeto inclui `Dockerfile` e `render.yaml`. A imagem instala Python e Tesseract; o servidor usa `0.0.0.0` e a porta `PORT` fornecida pelo Render.

1. Publique esta pasta em um repositório GitHub.
2. No [Render](https://dashboard.render.com), escolha **New → Blueprint** e conecte o repositório.
3. Selecione o `render.yaml` da raiz e confirme a criação do serviço `last-war-battle-manager`.
4. Aguarde o deploy e abra o endereço HTTPS exibido pelo Render.

O plano configurado é gratuito e pode suspender o serviço quando inativo. Na versão hospedada, os prints são enviados ao servidor Render para processamento; o cadastro e o histórico continuam armazenados no navegador. Os dados usados em `localhost` não são migrados automaticamente para o endereço hospedado.

## Problemas comuns

- **Tesseract não encontrado:** instale-o ou execute `$env:TESSERACT_CMD='C:\caminho\tesseract.exe'` antes de iniciar o servidor.
- **Imagem não reconhecida:** confira a nitidez e os limites de nomes e pontos. Utilize os botões e o campo de pontos para corrigir manualmente.
- **Página não abre:** verifique a janela do servidor e se a porta 8000 está livre. Para outra porta, altere `--port` e o endereço aberto no navegador.
