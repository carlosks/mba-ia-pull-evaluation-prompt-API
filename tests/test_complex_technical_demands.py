from app.services.generator_service import (
    is_devops_database_request,
    is_supplier_bug,
    generate_devops_database_acceptance_criteria,
    generate_fallback_test_cases,
)


def test_identifies_complex_jenkins_sql_server_demand():
    demand = (
        "Criar uma pipeline Jenkins para executar, de forma controlada e auditável, "
        "um script DML no banco SQL Server de Produção, com aprovação manual, "
        "validação prévia e registro de evidências."
    )

    assert is_devops_database_request(demand) is True


def test_complex_jenkins_sql_server_demand_is_not_supplier_bug():
    demand = (
        "Criar uma pipeline Jenkins para executar DML no SQL Server de Produção "
        "com aprovação manual e auditoria."
    )

    assert is_supplier_bug(demand) is False


def test_devops_database_acceptance_criteria_mentions_required_controls():
    criteria = generate_devops_database_acceptance_criteria()
    text = " ".join(criteria).lower()

    assert "sql server" in text
    assert "jenkins" in text
    assert "produção" in text
    assert "aprovação manual" in text
    assert "credenciais" in text


def test_devops_database_fallback_test_cases_are_not_supplier_specific():
    demand = (
        "Criar uma pipeline Jenkins para executar DML no SQL Server de Produção "
        "com validação, aprovação e auditoria."
    )

    test_cases = generate_fallback_test_cases(demand)
    text = " ".join(test_cases).lower()

    assert "pipeline" in text
    assert "sql server" in text
    assert "jenkins" in text
    assert "fornecedor" not in text
    assert "cnpj" not in text
