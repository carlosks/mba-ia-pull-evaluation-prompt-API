import re
import unicodedata
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


KEYWORD_ALIASES = {
    "login": ["login", "logar", "autenticar", "autenticacao", "autenticação"],
    "logar": ["login", "logar", "autenticar", "autenticacao", "autenticação"],

    "erro": ["erro", "erro 500", "500", "falha", "problema"],
    "erro 500": ["erro", "erro 500", "500"],

    "perfil": ["perfil", "perfis"],
    "perfis": ["perfil", "perfis"],

    "multiplos perfis": ["multiplos perfis", "múltiplos perfis", "perfis"],
    "múltiplos perfis": ["multiplos perfis", "múltiplos perfis", "perfis"],

    "formulario": ["formulario", "formulário", "formularios", "formulários"],
    "formulário": ["formulario", "formulário", "formularios", "formulários"],

    "salvar": ["salvar", "salva", "salve", "gravado", "gravar", "mantido", "registradas"],
    "salva": ["salvar", "salva", "salve", "gravado", "gravar", "mantido", "registradas"],

    "dashboard": ["dashboard", "painel"],

    "tela": ["tela", "pagina", "página"],
    "branco": ["branco", "em branco", "vazio", "vazia"],
    "tela em branco": ["tela em branco", "pagina em branco", "página em branco", "branco"],
}


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def semantic_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([a, b])

    score = cosine_similarity(vectors[0], vectors[1])[0][0]

    return float(score)


def get_aliases(keyword: str) -> List[str]:
    keyword_normalized = normalize_text(keyword)

    aliases = KEYWORD_ALIASES.get(keyword_normalized, [keyword_normalized])

    return [normalize_text(alias) for alias in aliases]


def keyword_score(text: str, keywords: List[str]) -> float:
    if not text or not keywords:
        return 0.0

    text_normalized = normalize_text(text)

    matches = 0

    for keyword in keywords:
        aliases = get_aliases(keyword)

        found = any(alias in text_normalized for alias in aliases)

        if found:
            matches += 1

    return matches / len(keywords)


def structure_score(user_story: str) -> float:
    if not user_story:
        return 0.0

    text = normalize_text(user_story)

    pattern = r"como um .*eu quero .*para que .*"

    if re.search(pattern, text):
        return 1.0

    return 0.0


def final_score(semantic: float, keyword: float, structure: float) -> float:
    score = (semantic + keyword + structure) / 3
    return round(score, 2)