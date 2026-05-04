from langchain_openai import ChatOpenAI


def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def generate_user_story(bug: str):
    llm = get_llm()

    prompt = f"""
Transforme o bug em uma User Story clara.

BUG:
{bug}

Formato obrigatório:
Como um <usuário>, eu quero <ação>, para que <benefício>.

Critérios de Aceitação:
Dado ...
Quando ...
Então ...
"""

    res = llm.invoke(prompt)
    return res.content


# 🔥 NOVO: melhorar user story
def improve_user_story(bug: str, story: str):
    llm = get_llm()

    prompt = f"""
A seguinte user story está ruim ou incompleta.

BUG ORIGINAL:
{bug}

USER STORY ATUAL:
{story}

Reescreva a user story melhorando:

- Clareza
- Precisão
- Critérios de aceitação completos
- Formato correto

Formato obrigatório:
Como um <usuário>, eu quero <ação>, para que <benefício>.

Critérios:
Dado ...
Quando ...
Então ...
"""

    res = llm.invoke(prompt)
    return res.content