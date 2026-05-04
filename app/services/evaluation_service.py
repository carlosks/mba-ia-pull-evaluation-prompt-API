import re
import unicodedata
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# 🔤 NORMALIZAÇÃO
def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# 🔎 TOKENIZAÇÃO
def tokenize(text: str):
    stopwords = {
        "a","o","e","de","do","da","para","que","com",
        "um","uma","no","na","nos","nas"
    }
    words = normalize_text(text).split()
    return {w for w in words if w not in stopwords and len(w) > 2}


# 📊 F1 PROXY
def f1_proxy(bug: str, story: str):
    bug_terms = tokenize(bug)
    story_terms = tokenize(story)

    if not bug_terms or not story_terms:
        return 0.0

    inter = bug_terms.intersection(story_terms)

    precision = len(inter) / len(story_terms)
    recall = len(inter) / len(bug_terms)

    if precision + recall == 0:
        return 0.0

    return round(2 * (precision * recall) / (precision + recall), 2)


# 🧠 SIMILARIDADE SEMÂNTICA
def semantic_similarity(bug: str, story: str):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    v1 = embeddings.embed_query(bug)
    v2 = embeddings.embed_query(story)

    sim = cosine_similarity([v1], [v2])[0][0]

    length_ratio = min(len(story) / max(len(bug), 1), 5)
    sim_adjusted = sim * (1 + (length_ratio * 0.05))

    return round(min(sim_adjusted, 1.0), 2)


# 🧱 ESTRUTURA
def structure_score(story: str):
    normalized = normalize_text(story)

    checks = {
        "como_um": "como um" in normalized,
        "eu_quero": "eu quero" in normalized,
        "para_que": "para que" in normalized,
        "criterios": (
            "dado" in normalized and
            "quando" in normalized and
            "entao" in normalized
        )
    }

    score = sum(checks.values()) / len(checks)
    return round(score, 2), checks


# 🤖 LLM JUDGE
def llm_judge(bug: str, story: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
Avalie a user story abaixo.

BUG:
{bug}

USER STORY:
{story}

Avalie de 0 a 1:
- clareza
- precisão
- utilidade
- critérios

Retorne JSON:
{{"clarity":0.0,"precision":0.0,"usefulness":0.0,"criteria":0.0}}
"""

    res = llm.invoke(prompt)

    import json
    try:
        return json.loads(res.content)
    except:
        return {
            "clarity":0.7,
            "precision":0.7,
            "usefulness":0.7,
            "criteria":0.7
        }


# 🔥 EXTRAÇÃO ROBUSTA DE CENÁRIOS (FUNCIONA MESMO EM UMA LINHA)
def extract_scenarios(text: str):
    text = text.lower()

    # quebra artificial
    text = text.replace(" dado", "\nDado")

    lines = text.split("\n")
    raw_scenarios = []
    current = ""

    for line in lines:
        line = line.strip()

        if line.startswith("dado"):
            if current:
                raw_scenarios.append(current)
            current = line

        elif line.startswith("quando") or line.startswith("entao"):
            current += " " + line

    if current:
        raw_scenarios.append(current)

    # 🔥 NORMALIZA PARA COMPARAÇÃO
    def normalize(s):
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        s = re.sub(r'[^a-z0-9 ]', '', s)
        return s.strip()

    unique = []
    seen = []

    for s in raw_scenarios:
        ns = normalize(s)

        # 🔥 compara similaridade simples (containment)
        if not any(ns in x or x in ns for x in seen):
            seen.append(ns)
            unique.append(s)

    return unique


# 🔍 NOVOS CENÁRIOS
def detect_new_scenarios(old_story: str, new_story: str):
    old = set(extract_scenarios(old_story))
    new = set(extract_scenarios(new_story))
    return list(new - old)


# 🚀 DETECÇÃO DE EXPANSÃO
def detect_expansion(bug: str, story: str):
    length_ratio = len(story) / max(len(bug), 1)
    scenarios = len(extract_scenarios(story))

    expanded = length_ratio > 2 or scenarios >= 2

    bonus = 0.0
    if expanded:
        bonus = min(0.1, (length_ratio * 0.02) + (scenarios * 0.01))

    return {
        "detected": expanded,
        "scenarios_added": scenarios,
        "bonus": round(bonus, 2),
        "label": f"Story enriquecida (+{scenarios} cenários)" if expanded else None
    }


# 🎯 AVALIAÇÃO FINAL
def evaluate_all(bug: str, story: str):
    f1 = f1_proxy(bug, story)
    sem = semantic_similarity(bug, story)
    struct, checks = structure_score(story)
    judge = llm_judge(bug, story)

    judge_score = round(sum(judge.values()) / len(judge), 2)

    expansion = detect_expansion(bug, story)

    # peso adaptativo
    f1_weight = 0.05 if len(story) < 2 * len(bug) else 0.01

    base_score = (
        f1 * f1_weight +
        sem * 0.35 +
        struct * 0.25 +
        judge_score * 0.35
    )

    # bônus estrutura perfeita
    if struct == 1.0:
        base_score += 0.05

    # bônus expansão
    final = round(min(base_score + expansion["bonus"], 1.0), 2)

    if final >= 0.9:
        status = "approved"
    elif final >= 0.75:
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
            "judge": judge_score
        },
        "checks": checks,
        "expansion": expansion
    }