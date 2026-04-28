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

Não escreva títulos.
Não escreva explicações.
Não escreva código.
Não escreva listas fora desse formato.
"""),
    ("user", "Bug report:\n{bug_report}")
])

hub.push(
    "carlosks/bug_to_user_story_v15",
    prompt
)

print("✅ Prompt v15 criado com sucesso no Hub!")
