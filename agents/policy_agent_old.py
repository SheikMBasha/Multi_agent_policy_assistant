# from autogen import AssistantAgent
# from shared.llm_config import llm_config
# from rag.retriever import get_relevant_chunks
# import datetime
# import os
#
# def format_prompt_with_context(query):
#     chunks = get_relevant_chunks(query)
#
#     # Setup timestamped log entry
#     timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     log_path = "rag_trace_log.txt"
#
#     with open(log_path, "a", encoding="utf-8") as f:
#         f.write(f"\n🕓 [{timestamp}] Query: {query}\n")
#         f.write(f"🔍 Retrieved {len(chunks)} chunks from RAG\n")
#         print(f"\n🕓 [{timestamp}] Query: {query}")
#         print(f"🔍 Retrieved {len(chunks)} chunks from RAG")
#
#         if not chunks:
#             f.write("⚠️ No relevant chunks found. Using fallback prompt.\n")
#             print("⚠️ No relevant chunks found. Using fallback prompt.")
#             return f"""
# You are the PolicyAgent.
#
# No information was found in the retrieved documents to answer the question below.
# Please respond with a general answer, and say clearly:
# "This answer is not based on the retrieved documents."
#
# Question: {query}
#
# Answer:
# """
#
#         # If chunks exist, log each one
#         for i, doc in enumerate(chunks):
#             preview = doc.page_content[:200].strip()
#             f.write(f"📄 Chunk {i+1}: {preview}...\n")
#             print(f"📄 Chunk {i+1}: {preview}...")
#
#         f.write("-" * 80 + "\n")
#
#     # Combine context and citations for LLM prompt
#     context = "\n---\n".join([doc.page_content.strip() for doc in chunks])
#     citations = "\n".join([f"📄 Chunk {i+1}: {doc.page_content[:200].strip()}..." for i, doc in enumerate(chunks)])
#
#     return f"""
# You are the PolicyAgent.
#
# Use ONLY the context below to answer the user's question.
# If the context is unrelated or insufficient, clearly say:
# "This answer is not based on the retrieved documents."
#
# Context:
# {context}
#
# Question: {query}
#
# Answer:
#
# (Include for debug/audit)
# Confidence: High
# Sources:
# {citations}
# """
#
# # 🧠 Create the assistant agent
# policy_agent = AssistantAgent(
#     name="PolicyAgent",
#     llm_config=llm_config,
#     system_message="You are the PolicyAgent. Answer using provided document context. Always say '[final_answer]' at the end."
# )
#
# # Register the reply logic
# @policy_agent.register_for_execution()
# def handle_policy_query(_, messages, **__):
#     query = messages[-1]["content"]
#     prompt = format_prompt_with_context(query)
#     return True, prompt
