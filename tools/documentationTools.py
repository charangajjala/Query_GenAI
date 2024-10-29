from datetime import date
from langchain.agents import Tool
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain_community.vectorstores import FAISS
 
def get_chain(self):
        prompt_template = """
        Answer the question as detailed as possible from the provided context. If the answer is not in the provided context, say, "The answer is not available in the context."

        Context:\n{context}\n
        Question:\n{question}\n

        Answer:
        """
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        return load_qa_chain(self.model, chain_type="stuff", prompt=prompt)

def get_user_response(self, user_question):
        vector_store = FAISS.load_local("faiss_openai_index", self.embeddings, allow_dangerous_deserialization=True)
        docs = vector_store.similarity_search(user_question)
        chain = self.get_chain()
        response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
        return response["output_text"]


documentationTools = [
    Tool(
        name="Documentation",
        func=get_user_response,
        description="Answer troubleshooting or configuration questions about the SPOT robot."
    )
]