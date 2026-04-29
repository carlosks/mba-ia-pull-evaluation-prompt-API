from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.pipeline import gerar_user_story, gerar_api

app = FastAPI(
    title="Bug to API SaaS",
    description="SaaS que transforma bugs em User Stories, Critérios de Aceitação, APIs e Testes.",
    version="1.0.0"
)


class BugInput(BaseModel):
    bug: str


class UserStoryInput(BaseModel):
    user_story: str


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "Bug to API SaaS"
    }


@app.post("/generate-story")
def generate_story(input_data: BugInput):
    try:
        user_story, criterios, data = gerar_user_story(input_data.bug)

        return {
            "bug": input_data.bug,
            "user_story": user_story,
            "acceptance_criteria": criterios
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-api")
def generate_api(input_data: UserStoryInput):
    try:
        codigo = gerar_api(input_data.user_story)

        return {
            "user_story": input_data.user_story,
            "generated_code": codigo
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-full")
def generate_full(input_data: BugInput):
    try:
        user_story, criterios, data = gerar_user_story(input_data.bug)

        codigo = gerar_api(user_story)

        return {
            "bug": input_data.bug,
            "user_story": user_story,
            "acceptance_criteria": criterios,
            "generated_api": codigo
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))