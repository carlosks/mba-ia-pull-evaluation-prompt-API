import json
import os

from app.services.generator_service import generate_all
from src.evaluation.metrics import (
    semantic_similarity,
    keyword_score,
    structure_score,
    final_score
)


# 🔹 Caminho do dataset (sem hardcode absoluto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "datasets", "bug_to_user_story.jsonl")


def load_dataset():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset não encontrado em: {DATASET_PATH}")

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def evaluate():
    data = load_dataset()

    results = []

    print("\n" + "=" * 50)
    print("AVALIAÇÃO COMPLETA DE PROMPTS")
    print("=" * 50 + "\n")

    for i, item in enumerate(data, 1):
        bug = item["bug"]
        expected = item["expected_user_story"]
        keywords = item.get("expected_keywords", [])

        try:
            output = generate_all(bug)

            user_story = output.get("user_story", "")
            print(f"   User Story Gerada: {user_story}")
            acceptance_criteria = output.get("acceptance_criteria", [])

            # 🔹 Métricas
            sem = semantic_similarity(user_story, expected)
            key = keyword_score(user_story, keywords)
            struct = structure_score(user_story)

            score = final_score(sem, key, struct)

            print(f"[{i}] BUG: {bug}")
            print(f"   Score Final: {score}")
            print(f"   Semantic: {sem:.2f}")
            print(f"   Keywords: {key:.2f}")
            print(f"   Structure: {struct:.2f}")
            print("-" * 50)

            results.append(score)

        except Exception as e:
            print(f"[{i}] ❌ ERRO ao processar: {bug}")
            print(f"   Detalhe: {str(e)}")
            print("-" * 50)

    if not results:
        print("❌ Nenhum resultado válido.")
        return 0

    avg = round(sum(results) / len(results), 2)

    print("\n" + "=" * 50)
    print(f"🎯 SCORE MÉDIO FINAL: {avg}")
    print("=" * 50 + "\n")

    return avg


if __name__ == "__main__":
    evaluate()