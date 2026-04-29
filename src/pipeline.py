import os
import json
from openai import OpenAI


# ==============================
# CLIENTE OPENAI
# ==============================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==============================
# GERAR USER STORY + CRITÉRIOS
# ==============================

def gerar_user_story(bug: str):
    prompt = f"""
Você é um especialista em engenharia de software.

Dado o bug abaixo, gere uma resposta em JSON válido com:

- user_story (string)
- acceptance_criteria (lista de strings)

Bug:
{bug}

Responda APENAS em JSON válido.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)
    except Exception:
        raise Exception(f"Erro ao interpretar JSON da IA:\n{content}")

    return (
        data.get("user_story", ""),
        data.get("acceptance_criteria", []),
        data
    )


# ==============================
# GERAR API (FASTAPI)
# ==============================

def gerar_api(user_story: str):
    prompt = f"""
Você é um arquiteto de software.

Com base na User Story abaixo, gere um código completo em FastAPI.

Requisitos:
- Código funcional
- Validações com Pydantic
- Endpoint POST
- Tratamento de erro
- Comentários no código

User Story:
{user_story}

Retorne apenas código Python.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    codigo = response.choices[0].message.content

    return codigo