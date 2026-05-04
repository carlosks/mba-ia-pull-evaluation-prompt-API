import re
from difflib import SequenceMatcher
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# 1. Estrutura da User Story
# =========================
def check_structure(user_story: str) -> float:
    patterns = [
        r"como um",
        r"eu quero",
        r"para que"
    ]

    matches = sum(1 for p in patterns if re.search(p, user_story.lower()))
    return matches / len(patterns)  # 0 → 1


# =========================
# 2. Critérios de aceitação
# =========================
def check_acceptance_criteria(criteria: list) -> float:
    if not criteria:
        return 0

    score = 0

    # quantidade mínima
    if len(criteria) >= 3:
        score += 0.5

    # qualidade (frases com verbo)
    valid = sum(1 for c in criteria if len(c.split()) > 5)
    score += (valid / len(criteria)) * 0.5

    return min(score, 1.0)


# =========================
# 3. Similaridade semântica (simples)
# =========================
def semantic_similarity(bug: str, story: str) -> float:
    return SequenceMatcher(None, bug.lower(), story.lower()).ratio()


# =========================
# 4. IA como Juiz (LLM)
# =========================
def llm_judge(bug: str, story: str) -> float:
    try:
        prompt = f"""
Avalie a qualidade da user story abaixo em relação ao bug.

BUG:
{bug}

USER STORY:
{story}

Responda apenas com um número de 0 a 1.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        score = float(response.choices[0].message.content.strip())
        return max(0, min(score, 1))

    except:
        return 0.5  # fallback


# =========================
# 5. Avaliação final
# =========================
def evaluate(bug: str, user_story_data: dict):
    user_story = user_story_data.get("user_story", "")
    criteria = user_story_data.get("acceptance_criteria", [])

    structure_score = check_structure(user_story)
    criteria_score = check_acceptance_criteria(criteria)
    semantic_score = semantic_similarity(bug, user_story)
    judge_score = llm_judge(bug, user_story)

    # pesos
    final_score = (
        structure_score * 0.2 +
        criteria_score * 0.3 +
        semantic_score * 0.2 +
        judge_score * 0.3
    )

    status = "approved" if final_score >= 0.7 else "needs_improvement"

    return {
        "score": round(final_score, 2),
        "status": status,
        "metrics": {
            "structure": round(structure_score, 2),
            "criteria": round(criteria_score, 2),
            "semantic": round(semantic_score, 2),
            "judge": round(judge_score, 2),
        }
    }