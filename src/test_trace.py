from dotenv import load_dotenv
import os

from langchain.callbacks import tracing_v2_enabled
from langchain_openai import ChatOpenAI

load_dotenv(".env")

llm = ChatOpenAI(model="gpt-4o-mini")

def run_test():
    return llm.invoke("Diga apenas: OK").content


with tracing_v2_enabled(project_name=os.getenv("LANGSMITH_PROJECT")):
    print(run_test())