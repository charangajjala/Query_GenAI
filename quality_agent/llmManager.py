from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import os

class LLMManager:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            temperature=0,
            azure_deployment=os.getenv('OPENAI_DEPLOYMENT_NAME'),
            azure_endpoint=os.getenv('OPENAI_DEPLOYMENT_ENDPOINT'),
            api_key=os.getenv('OPENAI_API_KEY'),
            api_version=os.getenv('OPENAI_DEPLOYMENT_VERSION'),
            streaming=True
        )
        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_TEXT_EMBEDDING_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("AZURE_OPENAI_TEXT_EMBEDDING_DEPLOYMENT_VERSION"),
            azure_endpoint=os.getenv('OPENAI_DEPLOYMENT_ENDPOINT'),
        )

    def invoke(self, prompt: ChatPromptTemplate, **kwargs) -> str:
        messages = prompt.format_messages(**kwargs)
        response = self.llm.invoke(messages)
        return response.content