import os
import time
import traceback
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
    if not os.path.exists(os.path.join(vectorstore_path, "index.faiss")):
        print("Vector store index file not found, building it...")
        build_vectorstore()
    else:
        # Load the existing index with cached embeddings
        try:
            print("Loading vector store...")
            # Suppress deprecation warnings during loading
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                db = FAISS.load_local(
                    vectorstore_path, 
                    OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY")),
                    allow_dangerous_deserialization=True
                )
            print("Vector store loaded successfully")
        except Exception as e:
            print(f"Error loading vector store: {e}")
            print(traceback.format_exc())
            # Return empty list instead of raising the exception
            return []
    
    # Doing Similarity search
    try:
        print(f"Performing similarity search with K = {k}")
        start_time = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = db.similarity_search(query, k=k, search_params={"nprobe": 2})
        search_time = time.time() - start_time
        print(f"Search completed in {search_time:.2f} seconds")
        print(f"Search completed in {search_time:.2f}")
        print(f"Found {len(results)} chunks")

        # Verify we have a valid list to return
        if results is None:
            print("Results is None, returning empty list")
            return []
                
        if not isinstance(results, list):
            print(f"Results is not a list (type: {type(results)}), returning empty list")
            return []
                
        return results
    except Exception as e:
        # Catch-all exception handler
        print(f"Unexpected error in get_relevant_chunks: {e}")
        print(traceback.format_exc())
        return []  # Return empty list as fallback