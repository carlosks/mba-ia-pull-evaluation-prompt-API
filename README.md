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

## Fila de gerações

As gerações rodam em segundo plano. O fluxo recomendado é:

1. `POST /jobs` com `{"kind": "generate-solution", "bug": "..."}` → responde `202` com o `id`.
2. `GET /jobs/{id}` até `status` ser `succeeded` (resultado em `result`) ou `failed` (`error_message`).
3. `GET /jobs` lista as gerações recentes do usuário.

As rotas antigas `/projects/generate*` continuam funcionando (síncronas), por compatibilidade.

Gerações que falham não descontam da cota mensal. Gerações na fila contam para a cota,
para impedir que alguém enfileire várias com um único crédito restante.

Limitação atual: a fila roda dentro do processo da API. Com mais de uma instância,
troque o executor por RQ/Celery + Redis (a tabela `generation_jobs` continua a mesma).

## Custo por geração

Cada registro em `usage_logs` guarda modelo, tokens de entrada/saída, custo estimado em US$
e duração. O relatório `GET /admin/usage-costs?days=30` mostra, por plano, o custo total e o
custo médio por geração: é a base para definir preço e limites dos planos.

## Banco de dados e migrações

O esquema é versionado com Alembic. No startup a aplicação aplica as migrações pendentes
automaticamente; bancos antigos (anteriores ao Alembic) são ajustados e marcados na primeira vez.

```bash
alembic upgrade head                         # aplica manualmente
alembic revision --autogenerate -m "descrição"  # nova migração após alterar app/models.py
```

## Armazenamento dos projetos gerados

Os arquivos são escritos em `GENERATED_PROJECTS_DIR`. No Render esse disco é apagado a cada
deploy; para não perder os projetos dos clientes, configure um bucket S3 compatível
(AWS S3, Cloudflare R2, MinIO) com `STORAGE_BUCKET`, `STORAGE_ENDPOINT_URL`,
`AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`. Cada projeto é enviado como `.zip` ao ser
gerado e restaurado automaticamente quando alguém o acessa.
