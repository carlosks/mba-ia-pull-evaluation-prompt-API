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