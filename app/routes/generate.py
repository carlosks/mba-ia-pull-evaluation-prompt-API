from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm_service import generate_user_story, improve_user_story
from app.services.evaluation_service import evaluate_all
from app.services.diff_service import build_improvement

router = APIRouter()


class BugRequest(BaseModel):
    description: str


@router.post("/generate-project")
def generate_project(data: BugRequest):
    bug = data.description

    # 1. geração inicial
    original_story = generate_user_story(bug)
    story = original_story

    # 2. avaliação inicial
    evaluation = evaluate_all(bug, story)

    # controle de melhoria
    max_attempts = 2
    attempt = 0
    improved = False

    # 🔥 loop inteligente de auto-correção
    while evaluation["score"] < 0.85 and attempt < max_attempts:
        new_story = improve_user_story(bug, story)
        new_eval = evaluate_all(bug, new_story)

        # 🔥 regra menos conservadora
        if (
            new_eval["score"] > evaluation["score"] or
            new_eval["metrics"]["structure"] > evaluation["metrics"]["structure"] or
            evaluation["status"] != "approved"
        ):
            story = new_story
            evaluation = new_eval
            improved = True

        attempt += 1

    # 🔥 diff + explicação + original (para UI)
    improvement_data = None
    if improved:
        improvement_data = build_improvement(bug, original_story, story)
        improvement_data["original"] = original_story

    # retorno final
    return {
        "user_story": story,
        "evaluation": evaluation,
        "auto_improved": improved,
        "improvement": improvement_data
    }