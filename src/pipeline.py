import os
import json
import re
from openai import OpenAI


# ==============================
# CLIENTE OPENAI
# ==============================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==============================
# FUNÇÃO AUXILIAR (LIMPEZA)
# ==============================

def limpar_json(texto: str) -> str:
    """
    Remove markdown e lixo comum da resposta da IA
    """
    texto = re.sub(r"```json|```", "", texto)
    texto = texto.strip()
    return texto


# ==============================
# GERAR USER STORY + CRITÉRIOS
# ==============================

def gerar_user_story(bug: str):
    prompt = f"""
Você é um especialista em engenharia de software.

Dado o bug abaixo, gere um JSON válido com:

- user_story (string)
- acceptance_criteria (lista de strings)

IMPORTANTE:
- NÃO use ```json
- NÃO use markdown
- Responda SOMENTE JSON puro

Bug:
{bug}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content

    # 🔥 limpeza
    content = limpar_json(content)

    try:
        data = json.loads(content)
    except Exception:
        # 🔥 fallback inteligente
        return (
            "Não foi possível gerar user story automaticamente.",
            ["Erro ao interpretar resposta da IA"],
            {"raw_response": content}
        )

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

Com base na User Story abaixo, gere código completo em FastAPI.

Requisitos:
- Código funcional
- Pydantic para validação
- Endpoint POST
- Tratamento de erro
- Comentários claros

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

    # opcional: limpar markdown também
    codigo = re.sub(r"```python|```", "", codigo).strip()

    return codigo