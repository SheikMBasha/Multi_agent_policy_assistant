# force_build_index.py
import os
import shutil
from rag.retriever import build_vectorstore

# Path to the vector store
vectorstore_path = "rag/faiss_index"

# Remove existing directory if it exists
if os.path.exists(vectorstore_path):
    print(f"Removing existing directory: {vectorstore_path}")
    shutil.rmtree(vectorstore_path)

# Create fresh directory
os.makedirs(vectorstore_path, exist_ok=True)

# Build the vector store
print("Building new vector store...")
build_vectorstore()
print("Vector store built successfully!")