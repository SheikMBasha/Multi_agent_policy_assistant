"""Policy agent implementation with RAG for answering policy questions"""

import datetime
from typing import Dict, Any, List
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext

class PolicyAgent(SimplifiedAgent):
    """Handles policy related queries with RAG support"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="PolicyAgent",
            system_message="""
You are the PolicyAgent. 
Answer using provided document context. 
Always say '[final_answer]' at the end.
""",
            llm_config=llm_config,
            context=context
        )

    def _extract_info_from_message(self, message: str) -> None:
        """Identify and track the policy topic being discussed"""
        super()._extract_info_from_message(message)
        
        message_lower = message.lower()

        if "warranty" in message_lower or "guarantee" in message_lower:
            self.context.policy_topic = "warranty"
        elif "return" in message_lower or "exchange" in message_lower:
            self.context.policy_topic = "returns"
        elif "loan" in message_lower or "document" in message_lower:
            self.context.policy_topic = "financing"
        elif "service" in message_lower or "maintenance" in message_lower:
            self.context.policy_topic = "service"

    def generate_response(self, message: str) -> str:
        """Generate a response using RAG to retrieve relevant context"""
        try:
            # Extract info
            self._extract_info_from_message(message)
            
            # Get RAG context for the query
            from rag.retriever import get_relevant_chunks
            
            # Log the RAG call
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_path = "rag_trace_log.txt"
            
            # Get relevant chunks from RAG with defensive coding
            try:
                chunks = get_relevant_chunks(message)
                # Verify chunks is a list
                if not isinstance(chunks, list):
                    print(f"WARNING: chunks is not a list. Type: {type(chunks)}")
                    chunks = []
            except Exception as e:
                print(f"Error getting relevant chunks: {e}")
                chunks = []
            
            # Log retrieval information - with added safety checks
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n🕓 [{timestamp}] PolicyAgent RAG Call\n")
                    f.write(f"🗣️ Query: {message}\n")
                    f.write(f"🔍 Retrieved {len(chunks)} chunks from RAG\n")
                    
                    seen = set()
                    if chunks:
                        for i, doc in enumerate(chunks):
                            # Safety check to make sure doc is a valid object
                            if not hasattr(doc, 'page_content'):
                                print(f"WARNING: doc at index {i} has no page_content attribute")
                                continue
                                
                            preview = doc.page_content[:200].strip().replace("\n", " ")
                            if preview not in seen:
                                seen.add(preview)
                                f.write(f"📄 Chunk {i+1}: {preview}...\n")
                    else:
                        f.write("⚠️ No relevant chunks found. Using fallback prompt.\n")
                    
                    f.write("-" * 80 + "\n")
            except Exception as e:
                print(f"Error logging to rag_trace_log.txt: {e}")
                # Continue execution even if logging fails
                
            # Prepare the prompt based on whether we found relevant chunks
            if not chunks:
                print("If not chunks begin")
                prompt = f"""
    You are the PolicyAgent.

    No information was found in the retrieved documents to answer the question below.
    Please respond with a general answer, and say clearly:
    "This answer is not based on the retrieved documents."

    [NO-RAG]

    Question: {message}

    Answer:
    """
            else:
                # Safely join all chunk content
                print("chunks exists")
                try:
                    context_parts = []
                    for doc in chunks:
                        if hasattr(doc, 'page_content'):
                            context_parts.append(doc.page_content.strip())
                    
                    context = "\n---\n".join(context_parts)
                    
                    # Create citation info
                    citation_lines = []
                    for i, doc in enumerate(chunks):
                        if hasattr(doc, 'page_content'):
                            preview = doc.page_content[:200].strip().replace("\n", " ")
                            citation_lines.append(f"📄 Chunk {i+1}: {preview}...")
                    citations = "\n".join(citation_lines)
                except Exception as e:
                    print(f"Error creating context/citations: {e}")
                    # Fallback to no-RAG prompt if context creation fails
                    context = ""
                    citations = ""
                    
                # Use fallback if context creation failed
                if not context:
                    print("If not context begin")
                    prompt = f"""
    You are the PolicyAgent.

    There was an error processing the retrieved documents.
    Please respond with a general answer, and say clearly:
    "This answer is not based on the retrieved documents."

    [NO-RAG]

    Question: {message}

    Answer:
    """
                else:
                    # Create the prompt with context
                    print("Creating prompt with context")
                    prompt = f"""
    You are the PolicyAgent.

    Use ONLY the context below to answer the user's question.
    If the context is unrelated or insufficient, clearly say:
    "This answer is not based on the retrieved documents."

    [RAG-SOURCE]

    Context:
    {context}

    Question: {message}

    Answer:

    (Include for debug/audit)
    Confidence: High
    Sources:
    {citations}
    """
            
            # Format the message as a dictionary with role and content
            formatted_message = {
                "role": "user",
                "content": prompt
            }
            
            # Generate response using the underlying agent
            response = self.agent.generate_reply(messages=[formatted_message])

            print(f"Response from agent is {response}")
            
            # Personalize the response
            personalized_response = self.context.personalize(response)

            print(f"Personlized Response from agent is {personalized_response}")
            
            # Update conversation history
            self.context.add_to_history(self.name, personalized_response)
            
            return personalized_response
            
        except Exception as e:
            print(f"Error in PolicyAgent.generate_response: {e}")
            return f"I apologize, but I encountered an error while retrieving information about used car loans. Please try again or ask about a different topic. [final_answer]"
    

#     def generate_response(self, message: str) -> str:
#         """Generate a response using RAG to retrieve relevant context"""
#         # Extract info
#         self._extract_info_from_message(message)
        
#         # Get RAG context for the query
#         from rag.retriever import get_relevant_chunks
        
#         # Log the RAG call
#         timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         log_path = "rag_trace_log.txt"
        
#         # Get relevant chunks from RAG
#         chunks = get_relevant_chunks(message)
        
#         # Log retrieval information
#         with open(log_path, "a", encoding="utf-8") as f:
#             f.write(f"\n🕓 [{timestamp}] PolicyAgent RAG Call\n")
#             f.write(f"🗣️ Query: {message}\n")
#             f.write(f"🔍 Retrieved {len(chunks)} chunks from RAG\n")
            
#             seen = set()
#             if chunks:
#                 for i, doc in enumerate(chunks):
#                     preview = doc.page_content[:200].strip().replace("\n", " ")
#                     if preview not in seen:
#                         seen.add(preview)
#                         f.write(f"📄 Chunk {i+1}: {preview}...\n")
#             else:
#                 f.write("⚠️ No relevant chunks found. Using fallback prompt.\n")
            
#             f.write("-" * 80 + "\n")
        
#         # Prepare the prompt based on whether we found relevant chunks
#         if not chunks:
#             prompt = f"""
# You are the PolicyAgent.

# No information was found in the retrieved documents to answer the question below.
# Please respond with a general answer, and say clearly:
# "This answer is not based on the retrieved documents."

# [NO-RAG]

# Question: {message}

# Answer:
# """
#         else:
#             # Join all chunk content
#             context = "\n---\n".join([doc.page_content.strip() for doc in chunks])
            
#             # Create citation info
#             citation_lines = []
#             for i, doc in enumerate(chunks):
#                 preview = doc.page_content[:200].strip().replace("\n", " ")
#                 citation_lines.append(f"📄 Chunk {i+1}: {preview}...")
#             citations = "\n".join(citation_lines)
            
#             # Create the prompt with context
#             prompt = f"""
# You are the PolicyAgent.

# Use ONLY the context below to answer the user's question.
# If the context is unrelated or insufficient, clearly say:
# "This answer is not based on the retrieved documents."

# [RAG-SOURCE]

# Context:
# {context}

# Question: {message}

# Answer:

# (Include for debug/audit)
# Confidence: High
# Sources:
# {citations}
# """
        
#         # Format the message as a dictionary with role and content
#         formatted_message = {
#             "role": "user",
#             "content": prompt
#         }
        
#         # Generate response using the underlying agent
#         response = self.agent.generate_reply(messages=[formatted_message])
        
#         # Personalize the response
#         personalized_response = self.context.personalize(response)
        
#         # Update conversation history
#         self.context.add_to_history(self.name, personalized_response)
        
#         return personalized_response