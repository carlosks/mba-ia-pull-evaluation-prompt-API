from dotenv import load_dotenv
load_dotenv()

from langchain import hub
from langchain.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "COLE AQUI O CONTEÚDO DO SEU SYSTEM PROMPT"),
    ("user", "{user_story}")
])

hub.push(
    "carlosks/user_story_to_api_v1",
    prompt
)

print("✅ Prompt publicado no Hub")