from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def gerar_user_story(bug: str):
    prompt = f"""
    Converta o seguinte bug em:

    1. User Story
    2. Critérios de Aceitação

    Bug:
    {bug}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    texto = response.choices[0].message.content

    return texto, [], None


def gerar_api(user_story: str):
    prompt = f"""
    Gere uma API FastAPI baseada na seguinte User Story:

    {user_story}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content