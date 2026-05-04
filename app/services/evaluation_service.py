import re
import numpy as np
import unicodedata
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# 🔤 NORMALIZAÇÃO (resolve acentos)
def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# 🔎 TOKENIZAÇÃO
def tokenize(text: str):
    stopwords = {
        "a", "o", "e", "de", "do", "da", "para", "que", "com",
        "um", "uma", "no", "na", "nos", "nas"
    }

    words = normalize_text(text).split()
    return {w for w in words if w not in stopwords and len(w) > 2}


# 📊 F1 SIMPLIFICADO (proxy)
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
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    v1 = embeddings.embed_query(bug)
    v2 = embeddings.embed_query(story)

    sim = cosine_similarity([v1], [v2])[0][0]
    return round(float(sim), 2)


# 🧱 VALIDAÇÃO DE ESTRUTURA
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


# 🤖 AVALIAÇÃO COM LLM (judge)
def llm_judge(bug: str, story: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
Você é um avaliador rigoroso de user stories.

Avalie a qualidade da user story baseada no bug.

BUG:
{bug}

USER STORY:
{story}

Retorne JSON válido:
{{
  "clarity": 0.0,
  "precision": 0.0,
  "usefulness": 0.0,
  "criteria": 0.0
}}
"""

    res = llm.invoke(prompt)

    import json
    try:
        return json.loads(res.content)
    except:
        return {
            "clarity": 0.7,
            "precision": 0.7,
            "usefulness": 0.7,
            "criteria": 0.7
        }


# 🎯 AVALIAÇÃO FINAL (calibrada para SaaS)
def evaluate_all(bug: str, story: str):
    f1 = f1_proxy(bug, story)
    sem = semantic_similarity(bug, story)
    struct, checks = structure_score(story)
    judge = llm_judge(bug, story)

    judge_score = round(sum(judge.values()) / len(judge), 2)

    # 🔥 PESOS AJUSTADOS (importante)
    final = round(
        f1 * 0.05 +        # baixo peso
        sem * 0.35 +       # alto peso
        struct * 0.25 +    # médio
        judge_score * 0.35, # alto
        2
    )

    # 📊 CLASSIFICAÇÃO
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
        "checks": checks
    }