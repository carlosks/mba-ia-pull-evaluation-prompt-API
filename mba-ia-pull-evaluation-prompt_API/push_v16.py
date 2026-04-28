from dotenv import load_dotenv
load_dotenv()

from langchain import hub
from langchain.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", """Converta o bug report em uma User Story.

Use exatamente este formato:

Como um <usuário>,
eu quero <ação>,
para que <benefício>.

Critérios de Aceitação:
- Dado que ...
- Quando ...
- Então ...
- E ...
- E ...

IMPORTANTE:
- Use linguagem simples
- Evite variações de palavras
- Tente usar os mesmos termos do exemplo

==================================================
EXEMPLO 1 (PIPELINE)
==================================================

Bug:
Pipeline calcula valor errado com desconto

Resposta:
Como um vendedor gerenciando oportunidades no pipeline, eu quero que o valor total seja calculado corretamente quando aplico descontos, para que eu possa apresentar propostas precisas aos clientes.

Critérios de Aceitação:
- Dado que tenho uma oportunidade com múltiplos produtos
- Quando aplico um desconto percentual
- Então o desconto deve ser aplicado no valor total de todos os produtos
- E o valor final deve ser correto
- E o sistema deve mostrar o detalhamento

==================================================
EXEMPLO 2 (API)
==================================================

Bug:
API retorna dados sem permissão

Resposta:
Como o sistema, eu quero validar permissões antes de retornar dados de usuários, para que apenas usuários autorizados possam acessar informações pessoais de outros usuários.

Critérios de Aceitação:
- Dado que sou um usuário comum
- Quando tento acessar dados de outro usuário
- Então devo receber HTTP 403 Forbidden
- E apenas devo acessar meus próprios dados
- E administradores devem acessar todos os dados

==================================================
EXEMPLO 3 (RELATÓRIO)
==================================================

Bug:
Relatório demora muito

Resposta:
Como um gerente de vendas, eu quero gerar relatórios rapidamente, para que eu possa analisar dados sem esperar.

Critérios de Aceitação:
- Dado que solicito um relatório com muitos registros
- Quando aplico filtros
- Então o relatório deve ser gerado em menos de 30 segundos
- E não deve ocorrer timeout
- E o desempenho deve ser consistente
"""),
    ("user", "Bug report:\n{bug_report}")
])

hub.push(
    "carlosks/bug_to_user_story_v16",
    prompt
)

print("✅ Prompt v16 criado com sucesso no Hub!")