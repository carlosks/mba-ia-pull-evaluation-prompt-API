"""
Funções auxiliares para o projeto de otimização de prompts.
Versão limpa: somente OpenAI (gpt-4o-mini / gpt-4o), sem Gemini.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

# Carrega variáveis do .env
load_dotenv()


# =========================================================
# LLM (VERSÃO FINAL - SOMENTE OPENAI)
# =========================================================
def get_llm(model: Optional[str] = None, temperature: float = 0.0):
    """
    Retorna instância do LLM usando OpenAI.

    Args:
        model: Nome do modelo (usa LLM_MODEL do .env se None)
        temperature: Temperatura (0.0 = determinístico)

    Returns:
        Instância de ChatOpenAI
    """
    model_name = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY não configurada no .env\n"
            "Obtenha uma chave em: https://platform.openai.com/api-keys"
        )

    print(f"🔥 USANDO MODELO: {model_name}")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key
    )


def get_eval_llm(temperature: float = 0.0):
    """
    Retorna LLM específico para avaliação (usa EVAL_MODEL).
    """
    eval_model = os.getenv("EVAL_MODEL", "gpt-4o")
    return get_llm(model=eval_model, temperature=temperature)


# =========================================================
# YAML
# =========================================================
def load_yaml(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {file_path}")
    except yaml.YAMLError as e:
        print(f"❌ Erro ao parsear YAML: {e}")
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
    return None


def save_yaml(data: Dict[str, Any], file_path: str) -> bool:
    try:
        output_file = Path(file_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

        return True
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")
        return False


# =========================================================
# ENV
# =========================================================
def check_env_vars(required_vars: list) -> bool:
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print("❌ Variáveis de ambiente faltando:")
        for var in missing:
            print(f"   - {var}")
        print("\nConfigure-as no arquivo .env antes de continuar.")
        return False

    return True


# =========================================================
# FORMAT / PRINT
# =========================================================
def format_score(score: float, threshold: float = 0.9) -> str:
    symbol = "✓" if score >= threshold else "✗"
    return f"{score:.2f} {symbol}"


def print_section_header(title: str, char: str = "=", width: int = 50):
    print("\n" + char * width)
    print(title)
    print(char * width + "\n")


# =========================================================
# VALIDATION
# =========================================================
def validate_prompt_structure(prompt_data: Dict[str, Any]) -> tuple[bool, list]:
    errors = []

    required_fields = ["description", "system_prompt", "version"]
    for field in required_fields:
        if field not in prompt_data:
            errors.append(f"Campo obrigatório faltando: {field}")

    system_prompt = prompt_data.get("system_prompt", "").strip()
    if not system_prompt:
        errors.append("system_prompt está vazio")

    if "TODO" in system_prompt:
        errors.append("system_prompt ainda contém TODOs")

    techniques = prompt_data.get("techniques_applied", [])
    if len(techniques) < 2:
        errors.append(
            f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}"
        )

    return (len(errors) == 0, errors)


# =========================================================
# JSON EXTRACTION
# =========================================================
def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1

        if start != -1 and end > start:
            try:
                return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                pass

    return None