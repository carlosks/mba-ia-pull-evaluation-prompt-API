# Generated API

    ## User Story

    Como um usuário, eu quero que o sistema salve meus dados ao clicar no botão salvar, para que eu possa ter acesso a eles posteriormente.

    ## Acceptance Criteria

    - Ao clicar no botão salvar, os dados devem ser gravados no banco de dados.
- Uma mensagem de confirmação deve ser exibida após o salvamento bem-sucedido.
- Se houver um erro ao salvar, uma mensagem de erro deve ser exibida.
- Os dados salvos devem ser recuperáveis e exibidos corretamente após o salvamento.

    ## Como rodar

    Instale as dependências:

    pip install -r requirements.txt

    Execute a API:

    uvicorn app.main:app --reload

    Acesse a documentação:

    http://127.0.0.1:8000/docs
