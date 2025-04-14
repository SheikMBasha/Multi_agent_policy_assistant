from autogen import AssistantAgent
from shared.llm_config import llm_config
from rag.retriever import get_relevant_chunks
import datetime


def format_prompt_with_context(query):
    chunks = get_relevant_chunks(query)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = "rag_trace_log.txt"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n🕓 [{timestamp}] PolicyAgent RAG Call\n")
        f.write(f"🗣️ Query: {query}\n")
        f.write(f"🔍 Retrieved {len(chunks)} chunks from RAG\n")

        seen = set()
        if chunks:
            for i, doc in enumerate(chunks):
                preview = doc.page_content[:200].strip().replace("\n", " ")
                if preview not in seen:
                    seen.add(preview)
                    f.write(f"📄 Chunk {i+1}: {preview}...\n")
        else:
            f.write("⚠️ No relevant chunks found. Using fallback prompt.\n")

        f.write("-" * 80 + "\n")

    if not chunks:
        return f"""
You are the PolicyAgent.

No information was found in the retrieved documents to answer the question below.
Please respond with a general answer, and say clearly:
"This answer is not based on the retrieved documents."

[NO-RAG]

Question: {query}

Answer:
"""

    context = "\n---\n".join([doc.page_content.strip() for doc in chunks])
    citation_lines = []
    for i, doc in enumerate(chunks):
        preview = doc.page_content[:200].strip().replace("\n", " ")
        citation_lines.append(f"📄 Chunk {i+1}: {preview}...")
    citations = "\n".join(citation_lines)

    return f"""
You are the PolicyAgent.

Use ONLY the context below to answer the user's question.
If the context is unrelated or insufficient, clearly say:
"This answer is not based on the retrieved documents."

[RAG-SOURCE]

Context:
{context}

Question: {query}

Answer:

(Include for debug/audit)
Confidence: High
Sources:
{citations}
"""


policy_agent = AssistantAgent(
    name="PolicyAgent",
    llm_config=llm_config,
    system_message="You are the PolicyAgent. Answer using provided document context. Always say '[final_answer]' at the end."
)


@policy_agent.register_for_execution()
def handle_policy_query(_, messages, **__):
    query = messages[-1]["content"]
    prompt = format_prompt_with_context(query)
    return True, prompt
