# test_embeddings.py
import os
from dotenv import load_dotenv
import time
import sys

# Load environment variables
load_dotenv()

def test_langchain_community():
    print("Testing langchain_community.embeddings.OpenAIEmbeddings...")
    try:
        from langchain_community.embeddings import OpenAIEmbeddings
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment")
            return False
            
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        result = embeddings.embed_query("This is a test")
        
        print(f"Success! Got embedding with {len(result)} dimensions")
        return True
    except Exception as e:
        print(f"Error with langchain_community embeddings: {e}")
        return False

def test_langchain_openai():
    print("Testing langchain_openai.OpenAIEmbeddings...")
    try:
        from langchain_openai import OpenAIEmbeddings
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment")
            return False
            
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        result = embeddings.embed_query("This is a test")
        
        print(f"Success! Got embedding with {len(result)} dimensions")
        return True
    except Exception as e:
        print(f"Error with langchain_openai embeddings: {e}")
        return False

def test_vector_store():
    print("Testing FAISS vector store...")
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        from langchain.docstore.document import Document
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment")
            return False
            
        # Create simple documents
        docs = [
            Document(page_content="This is a test document about cars"),
            Document(page_content="This is a test document about loans"),
            Document(page_content="This is a test document about insurance")
        ]
        
        # Create embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        
        # Create vector store
        start_time = time.time()
        db = FAISS.from_documents(docs, embeddings)
        
        # Test search
        results = db.similarity_search("car loan", k=2)
        
        print(f"Success! Search completed in {time.time() - start_time:.2f} seconds")
        print(f"Found {len(results)} results")
        print(f"First result: {results[0].page_content}")
        
        return True
    except Exception as e:
        print(f"Error with FAISS vector store: {e}")
        return False

def print_package_versions():
    print("\nInstalled Package Versions:")
    for package in [
        "langchain", "langchain-community", "langchain-openai", 
        "langchain-core", "openai", "faiss-cpu"
    ]:
        try:
            module = __import__(package.replace("-", "_"))
            version = getattr(module, "__version__", "unknown")
            print(f"  {package}: {version}")
        except ImportError:
            print(f"  {package}: Not installed")

if __name__ == "__main__":
    print("=== LangChain Embeddings and Vector Store Test ===\n")
    
    # Print installed package versions
    print_package_versions()
    
    print("\n=== Testing Embeddings ===")
    community_success = test_langchain_community()
    openai_success = test_langchain_openai()
    
    print("\n=== Testing Vector Store ===")
    vectorstore_success = test_vector_store()
    
    print("\n=== Test Summary ===")
    print(f"LangChain Community Embeddings: {'✓' if community_success else '✗'}")
    print(f"LangChain OpenAI Embeddings: {'✓' if openai_success else '✗'}")
    print(f"FAISS Vector Store: {'✓' if vectorstore_success else '✗'}")
    
    if not (community_success or openai_success):
        print("\nRecommendation: Try reinstalling packages with:")
        print("pip uninstall -y langchain langchain-community langchain-core langchain-openai")
        print("pip install langchain==0.2.0 langchain-community==0.1.0 langchain-core==0.1.53 langchain-openai==0.1.0")