from langchain_cerebras import ChatCerebras
from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_fireworks import ChatFireworks
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from quality_agent.logger import setup_logger
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import os

logger = setup_logger(__name__)

llm_to_use = os.getenv("LLM_TO_USE", "groq")


class LLMManager:
    def __init__(self):
        try:
            logger.info("Initializing LLMManager")

            self.llm_for_router = ChatGroq(
                model="llama-3.1-70b-versatile",
                temperature=0.0,
                max_retries=2,
            )

            self.llm_for_documentation = ChatGroq(
                model="llama-3.1-70b-versatile",
                temperature=0.0,
                max_retries=2,
            )

            self.vision_llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                # other params...
            )

            if llm_to_use == "nvidia":
                self.llm = ChatNVIDIA(model="meta/llama3-70b-instruct", temperature=0)
            elif llm_to_use == "fireworks":
                self.llm = ChatFireworks(
                    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
                    temperature=0,
                    max_tokens=None,
                    timeout=None,
                    max_retries=2,
                )
            elif llm_to_use == "groq":
                self.llm = ChatGroq(
                    model="llama-3.1-70b-versatile",
                    temperature=0.0,
                    max_retries=2,
                )
            elif llm_to_use == "cerebras":
                self.llm = ChatCerebras(
                    model="llama3.1-70b",
                    temperature=0.0,
                    max_retries=2,
                )

            self.embeddings = ChatGroq(
                model="llama-3.1-70b-versatile",
                temperature=0.0,
                max_retries=2,
            )
            logger.info("LLMManager initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LLMManager: {e}")
            raise

    def invoke(self, prompt: ChatPromptTemplate, **kwargs) -> str:
        try:
            logger.info(f"Invoking LLM with prompt: {prompt}")
            messages = prompt.format_messages(**kwargs)
            response = self.llm.invoke(messages)
            logger.info(f"LLM response: {response.content}")
            return response.content
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            raise
