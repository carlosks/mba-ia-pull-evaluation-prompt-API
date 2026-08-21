from pathlib import Path


GENERATOR_SERVICE_PATH = Path("app/services/generator_service.py")


def test_main_prompts_use_technical_demand_language():
    content = GENERATOR_SERVICE_PATH.read_text(encoding="utf-8")

    assert "DEMANDA TÉCNICA" in content
    assert "Transforme a DEMANDA TÉCNICA abaixo" in content
    assert "Sua tarefa é receber uma DEMANDA TÉCNICA" in content


def test_main_prompts_do_not_use_legacy_bug_headings():
    content = GENERATOR_SERVICE_PATH.read_text(encoding="utf-8")

    assert "Transforme o BUG abaixo" not in content
    assert "Sua tarefa é receber um BUG" not in content
    assert "BUG:\n{bug}" not in content


def test_readme_language_accepts_demands_beyond_bugs():
    content = GENERATOR_SERVICE_PATH.read_text(encoding="utf-8")

    assert "## Demanda original" in content
    assert "a partir da demanda técnica" in content
    assert "## Bug original" not in content
