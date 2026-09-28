# MBA IA - Prompt Evaluation API

API em FastAPI para transformar bugs em:

- User Stories
- Critérios de Aceitação
- Análise Técnica
- Plano de Solução
- Código inicial gerado com OpenAI
- Projetos salvos em `generated_projects/`

## Tecnologias

- Python 3.11
- FastAPI
- Uvicorn
- OpenAI
- LangChain
- Pydantic

## Configuração local

Crie um arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sua_chave_openai
LLM_MODEL=gpt-4o-mini
ENVIRONMENT=development
## Segurança e variáveis de produção

Configure no provedor (Render, Docker etc.) antes do deploy:

| Variável | Obrigatória | Observação |
|---|---|---|
| `ENVIRONMENT` | sim | `production`. No Render, a aplicação já assume produção. |
| `SECRET_KEY` | sim | Mínimo 32 caracteres. Sem ela a aplicação não sobe em produção. |
| `OPENAI_API_KEY` | sim | Chave da OpenAI. |
| `DATABASE_URL` | sim | Postgres em produção. |
| `CREATE_DEV_ADMIN` | não | Ignorada em produção. |
| `CORS_ORIGINS` | não | Só se outro domínio for chamar a API. |
| `RATE_LIMIT_*` | não | Limites por IP de login, cadastro e geração. |

Gere uma `SECRET_KEY` com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Trocar a `SECRET_KEY` desconecta todos os usuários (os tokens antigos deixam de valer).
