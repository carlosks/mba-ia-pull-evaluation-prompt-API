from src.pipeline import gerar_user_story, gerar_api
from app.services.evaluator_service import evaluate


def generate_all(bug: str):
    # =========================
    # 1. Gerar User Story
    # =========================
    user_story, criteria, raw = gerar_user_story(bug)

    user_story_data = {
        "user_story": user_story,
        "acceptance_criteria": criteria
    }

    # =========================
    # 2. Gerar API
    # =========================
    api_code = gerar_api(user_story)

    # =========================
    # 3. Avaliar qualidade
    # =========================
    evaluation = evaluate(bug, user_story_data)

    # =========================
    # 4. Resposta final SaaS
    # =========================
    return {
        "bug": bug,
        "user_story": user_story,
        "acceptance_criteria": criteria,
        "api_code": api_code,
        "evaluation": evaluation
    }