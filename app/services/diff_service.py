import difflib
from langchain_openai import ChatOpenAI


def generate_diff(old: str, new: str):
    diff = difflib.ndiff(old.split(), new.split())

    changes = []
    for d in diff:
        if d.startswith("+ "):
            changes.append(f"+ {d[2:]}")
        elif d.startswith("- "):
            changes.append(f"- {d[2:]}")

    return changes


def explain_changes(bug: str, old: str, new: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
Explique de forma simples o que mudou entre duas user stories.

BUG:
{bug}

ANTES:
{old}

DEPOIS:
{new}

Explique:
- o que foi melhorado
- por que ficou melhor

Resposta curta e objetiva.
"""

    res = llm.invoke(prompt)
    return res.content


def build_improvement(bug: str, old: str, new: str):
    return {
        "diff": generate_diff(old, new),
        "explanation": explain_changes(bug, old, new)
    }