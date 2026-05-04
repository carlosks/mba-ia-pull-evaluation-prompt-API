import re
import unicodedata
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# ==============================
# NORMALIZAÇÃO
# ==============================

def normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ==============================
# TOKENIZAÇÃO
# ==============================

STOPWORDS = {"a", "o", "e", "de", "do", "da", "para", "que", "com", "um", "uma"}

def tokenize(text: str):
    words = normalize(text).split()
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


# ==============================
# F1 SCORE
# ==============================

def f1_score(bug: str, story: str):
    bug_terms = set(tokenize(bug))
    story_terms = set(tokenize(story))

    if not bug_terms or not story_terms:
        return 0.0

    intersection = bug_terms & story_terms

    precision = len(intersection) / len(story_terms)
    recall = len(intersection) / len(bug_terms)

    if precision + recall == 0:
        return 0.0

    return round(2 * (precision * recall) / (precision + recall), 2)


# ==============================
# SIMILARIDADE SEMÂNTICA
# ==============================

def semantic_similarity(bug: str, story: str):
    emb = OpenAIEmbeddings(model="text-embedding-3-small")

    v1 = emb.embed_query(bug)
    v2 = emb.embed_query(story)

    sim = cosine_similarity([v1], [v2])[0][0]

    return round(float(sim), 2)


# ==============================
# ESTRUTURA
# ==============================

def structure_score(story: str):
    s = normalize(story)

    checks = {
        "como_um": "como um" in s,
        "eu_quero": "eu quero" in s,
        "para_que": "para que" in s,
        "criterios": "dado" in s and "quando" in s and "entao" in s
    }

    score = sum(checks.values()) / len(checks)

    return round(score, 2), checks


# ==============================
# JUDGE LLM
# ==============================

def llm_judge(bug: str, story: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
Avalie a qualidade desta user story em relação ao bug.

BUG:
{bug}

USER STORY:
{story}

Critérios:
- clareza
- precisão
- utilidade

Retorne JSON:
{{
  "clarity": 0-1,
  "precision": 0-1,
  "usefulness": 0-1
}}
"""

    try:
        res = llm.invoke(prompt)
        import json
        data = json.loads(res.content)

        score = sum(data.values()) / len(data)

        return round(score, 2)

    except:
        return 0.7


# ==============================
# EXTRAÇÃO DE CENÁRIOS
# ==============================

def extract_scenarios(story: str):
    lines = story.split("\n")
    scenarios = []

    current = []

    for line in lines:
        l = line.strip().lower()

        if l.startswith("dado"):
            if current:
                scenarios.append(" ".join(current))
                current = []
            current.append(l)

        elif l.startswith(("quando", "entao", "e")):
            current.append(l)

    if current:
        scenarios.append(" ".join(current))

    return scenarios


# ==============================
# EXPANSÃO
# ==============================

def detect_expansion(bug: str, story: str):
    base_len = len(bug)
    story_len = len(story)

    scenarios = extract_scenarios(story)

    expansion_ratio = story_len / max(base_len, 1)

    scenarios_bonus = max(0, len(scenarios) - 1)

    bonus = min(0.1, (expansion_ratio - 1) * 0.05 + scenarios_bonus * 0.02)

    return {
        "detected": expansion_ratio > 1.2,
        "scenarios_added": scenarios_bonus,
        "bonus": round(bonus, 2),
        "label": f"Story enriquecida (+{scenarios_bonus} cenários)"
    }


# ==============================
# AVALIAÇÃO FINAL
# ==============================

def evaluate(bug: str, story: str):

    f1 = f1_score(bug, story)
    sem = semantic_similarity(bug, story)
    struct, checks = structure_score(story)
    judge = llm_judge(bug, story)
    expansion = detect_expansion(bug, story)

    # 🔥 pesos
    base = (
        f1 * 0.35 +
        sem * 0.25 +
        struct * 0.2 +
        judge * 0.2
    )

    # 🔥 penalizações inteligentes
    penalty = 0.0

    if f1 < 0.5:
        penalty += 0.2

    if sem < 0.6:
        penalty += 0.15

    if struct < 0.5:
        penalty += 0.1

    # 🔥 score final
    final = round(min(base + expansion["bonus"] - penalty, 1.0), 2)

    # 🔥 status
    if final >= 0.9:
        status = "approved"
    elif final >= 0.7:
        status = "review"
    else:
        status = "bad"

    return {
        "score": final,
        "status": status,
        "metrics": {
            "f1": f1,
            "semantic": sem,
            "structure": struct,
            "judge": judge
        },
        "checks": checks,
        "expansion": expansion,
        "explanation": {
            "penalty": penalty,
            "base_score": round(base, 2)
        }
    }