import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from rag.loader import load_policy_documents

load_dotenv()

vectorstore_path = "rag/faiss_index"

def build_vectorstore():
    texts = load_policy_documents()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = [Document(page_content=chunk) for text in texts for chunk in splitter.split_text(text)]
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(vectorstore_path)

def get_relevant_chunks(query, k=3):
    if not os.path.exists(vectorstore_path):
        build_vectorstore()
    db = FAISS.load_local(vectorstore_path, OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY")), allow_dangerous_deserialization=True)
    return db.similarity_search(query, k=k)