# simplified_agents.py - Combines agents and handlers into a single module

import autogen
from typing import Dict, Any, Optional, List
import re
import json
from tools import calculateincentivetool

class ConversationContext:
    """Manages shared context across all agents in the conversation."""

    def __init__(self):
        # User Information
        self.user_name: Optional[str] = None
        self.conversation_started: bool = False
        self.turns_count: int = 0
        self.last_active_agent: Optional[str] = None

        # User specific information
        self.user_location: Optional[str] = None
        self.user_contact_info: Optional[str] = None

        # Conversation History
        self.message_history: List[Dict[str, str]] = []

        # Domain-specific information
        self.contract_apr: Optional[float] = None
        self.buy_rate: Optional[float] = None
        self.policy_topic: Optional[str] = None
        self.escalation_requested: bool = False

    def add_to_history(self, sender: str, message: str) -> None:
        """Add a message to the conversation history"""
        self.message_history.append({
            "sender": sender,
            "message": message
        })
        self.turns_count += 1

    def extract_name(self, message: str) -> Optional[str]:
        """Try to extract a name from user message."""
        name_patterns = [
            r"(?:I am|I'm|my name is|this is|call me) (\w+)",
            r"(\w+) (?:here|speaking)",
            r"^(\w+)$"  # Just a single word could be a name
        ]

        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # Extract name and capitalize first letter
                name = match.group(1)
                return name[0].upper() + name[1:] if len(name) > 1 else name.upper()

        return None

    def extract_location(self, message: str) -> Optional[str]:
        """Try to extract a location from user message."""
        # Simple zip code extraction
        zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', message)
        if zip_match:
            return zip_match.group(0)

        # City, State format extraction
        city_state_match = re.search(r'([A-Za-z\s]+),\s*([A-Za-z]{2,})', message)
        if city_state_match:
            return f"{city_state_match.group(1)}, {city_state_match.group(2)}"

        return None

    def extract_contact_info(self, message: str) -> Optional[str]:
        """Extract contact information from message."""
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', message)
        if email_match:
            return email_match.group(0)

        phone_match = re.search(r'(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', message)
        if phone_match:
            return phone_match.group(0)

        return None

    def get_recent_messages(self, count: int = 3) -> List[Dict[str, str]]:
        """Get the most recent messages from history."""
        return self.message_history[-count:] if self.message_history else []

    def personalize(self, message: str) -> str:
        """Add personalization to message if user_name is known"""
        if not self.user_name:
            return message

        # If message already contains the name, don't add it again
        if self.user_name in message:
            return message

        # Add name to beginning occasionally
        import random
        if random.random() < 0.3:  # 30% chance
            greeting_phrases = [
                f"{self.user_name}, ",
                f"Well {self.user_name}, ",
                f"So {self.user_name}, ",
            ]
            prefix = random.choice(greeting_phrases)
            return prefix + message[0].lower() + message[1:] if message else ""

        return message


class SimplifiedAgent:
    """Base class for all simplified agents that combine agent and handler functionality"""

    def __init__(self, name: str, system_message: str, llm_config: Dict[str, Any], context: ConversationContext):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config
        self.context = context

        # Create the underlying autogen agent
        self.agent = autogen.AssistantAgent(
            name=name,
            system_message=system_message,
            llm_config=llm_config
        )

    def generate_response(self, message: str) -> str:
        """Generate a response to the user message"""
        # Extract information from message
        self._extract_info_from_message(message)

        # Enrich message with context
        enriched_message = self._enrich_with_context(message)

        # Generate response using the underlying agent
        response = self.agent.generate_reply(enriched_message)

        # Personalize the response
        personalized_response = self.context.personalize(response)

        # Update conversation history
        self.context.add_to_history(self.name, personalized_response)

        return personalized_response

    def _extract_info_from_message(self, message: str) -> None:
        """Extract information from the message - overridden by subclasses"""
        # Base implementation just extracts name, location, and contact info
        name = self.context.extract_name(message)
        if name and not self.context.user_name:
            self.context.user_name = name

        location = self.context.extract_location(message)
        if location and not self.context.user_location:
            self.context.user_location = location

        contact = self.context.extract_contact_info(message)
        if contact and not self.context.user_contact_info:
            self.context.user_contact_info = contact

    def _enrich_with_context(self, message: str) -> str:
        """Add context information to the message"""
        # Gather context information
        context_info = {}

        # Add user information
        if self.context.user_name:
            context_info["user_name"] = self.context.user_name
        if self.context.user_location:
            context_info["user_location"] = self.context.user_location
        if self.context.user_contact_info:
            context_info["user_contact_info"] = self.context.user_contact_info

        # Add conversation information
        context_info["conversation_turns"] = self.context.turns_count
        if self.context.last_active_agent:
            context_info["last_active_agent"] = self.context.last_active_agent

        # Add recent message history
        recent_messages = self.context.get_recent_messages(3)
        if recent_messages:
            context_info["recent_conversation"] = [
                f"{msg['sender']}: {msg['message']}" for msg in recent_messages
            ]

        # Format as a structured prefix
        if context_info:
            context_prefix = f"[CONTEXT]\n{json.dumps(context_info, indent=2)}\n[/CONTEXT]\n\n"
            return context_prefix + message
        else:
            return message


class ModeratorAgent(SimplifiedAgent):
    """Determines which specialist agent should handle the query"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="ModeratorAgent",
            system_message="""
You are the RouterAgent for a dealer voice assistant. Based on the user query, You determine which agent should respond to the user query.

- @PricingAgent: Use only if the user is asking about incentives, dealer APR calculations, profit margins, or financial offer computations.
- @PolicyAgent: Use if the user is asking about loan policies, rules, required documents, eligibility, term length, maximum age, conditions, or approval criteria.
- @DealerAgent: Use if the user wants to log a complaint, report an issue, or give feedback about the dealership experience.

DO NOT respond or explain — just tag the appropriate agent with the full user query.

Examples:
- "What documents do I need?" → PolicyAgent
- "What's the current APR on a hatchback?" → PricingAgent
- "The dealer was rude to me" → DealerAgent
- "What is the loan term length?" → PolicyAgent
# Be Precise and respond with ONLY the agent name.
            """,
            llm_config=llm_config,
            context=context
        )

    def determine_agent(self, message: str) -> str:
        """Determine which agent should handle the message"""

        try:
            # Create a proper message list according to Autogen's expectations
            messages = [
                {
                    "role": "user",
                    "content": f"User query: {message}"
                }
            ]
            
            # Call the proper method with the message list
            response = self.agent.generate_reply(messages=messages)
            
            # Default to SmallTalk if no clear match
            valid_agents = ["PricingAgent", "PolicyAgent", "DealerAgent", "SmallTalkAgent"]
            for agent in valid_agents:
                if agent in response:
                    return agent
                    
            return "SmallTalkAgent"
        except Exception as e:
            import traceback
            print(f"DETAILED ERROR in moderator agent: {type(e)}, {e}")
            print(traceback.format_exc())
            
            # Temporary fallback
            if "loan" in message.lower():
                return "PricingAgent"
            return "SmallTalkAgent"

class PricingAgent(SimplifiedAgent):
    """Handles pricing related queries"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext, incentive_tool: calculateincentivetool):
        super().__init__(
            name="PricingAgent",
            system_message="""
You are the PricingAgent. You help calculate dealer incentives using contract APR and buy rate.

Steps:
1. Ask the user for both contract APR and buy rate.
2. If one is missing, ask naturally like a human would.
3. Use previously provided values (shared context) if available.
4. Once both values are available, compute incentive as:
   incentive = (contractAPR - buyRate) * 1000
5. Respond with the computed incentive clearly and end with [final_answer]

Respond as naturally and conversationally as possible.
""",
            llm_config=llm_config,
            context=context
        )

        self.incentive_tool = incentive_tool

    def generate_response(self, message: str) -> str:
        self._extract_info_from_message(message)

        # Check what information is missing
        if self.context.contract_apr is None:
            return "Could you please provide the contract APR?"

        if self.context.buy_rate is None:
            return "Could you please provide the buy rate?"

        # If both are available, call API
        try:
            incentive = self.incentive_tool.run(self.context.contract_apr, self.context.buy_rate)
            return f"The dealer incentive for the sale is ${incentive}.[final_answer]"
        except Exception as e:
            return f"Sorry, I encountered an error while calculating the incentive: {str(e)}"
    
        # Optionally, reset context after final answer
        self.context.contract_apr = None
        self.context.buy_rate = None

        return f"Dealer participation calculation result: {response} [final_answer]"    

    def _extract_info_from_message(self, message: str) -> None:
        """Extract pricing-related information from the message"""
        super()._extract_info_from_message(message)
        
        message_lower = message.lower()

        # Extract dealer name if present
        dealer_match = re.search(r'(?:dealer|dealership|at)(?:\s+is|\s*[:=])?\s*([A-Za-z0-9\s]+(?:Motors|Auto|Cars|Toyota|Honda|Ford|Chevrolet|BMW|Mercedes|Dealership))', message_lower)
        if dealer_match:
            # Clean up the dealer name (remove extra spaces, capitalize properly)
            dealer_name = dealer_match.group(1).strip()
            # Convert to title case (capitalize first letter of each word)
            dealer_name = ' '.join(word.capitalize() for word in dealer_name.split())
            self.context.dealer_name = dealer_name

        # Extract APR information if present
        apr_match = re.search(r'(?:contract apr|apr|interest)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)', message_lower)
        if apr_match:
            self.context.contract_apr = float(apr_match.group(1))

        # Extract buy rate information if present
        buy_rate_match = re.search(r'(?:buy rate|buy|rate)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)', message_lower)
        if buy_rate_match and "apr" not in message_lower[buy_rate_match.start()-5:buy_rate_match.start()]:
            self.context.buy_rate = float(buy_rate_match.group(1))




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

    def generate_response(self, message: str) -> str:
        """Generate a response using RAG to retrieve relevant context"""
        
        # Get RAG context for the query
        from rag.retriever import get_relevant_chunks
        import datetime
        
        # Log the RAG call
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = "rag_trace_log.txt"
        
        # Get relevant chunks from RAG
        chunks = get_relevant_chunks(message)
        
        # Log retrieval information
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n🕓 [{timestamp}] PolicyAgent RAG Call\n")
            f.write(f"🗣️ Query: {message}\n")
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
        
        # Prepare the prompt based on whether we found relevant chunks
        if not chunks:
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
            # Join all chunk content
            context = "\n---\n".join([doc.page_content.strip() for doc in chunks])
            
            # Create citation info
            citation_lines = []
            for i, doc in enumerate(chunks):
                preview = doc.page_content[:200].strip().replace("\n", " ")
                citation_lines.append(f"📄 Chunk {i+1}: {preview}...")
            citations = "\n".join(citation_lines)
            
            # Create the prompt with context
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
        
        # Personalize the response
        personalized_response = self.context.personalize(response)
        
        # Update conversation history
        self.context.add_to_history(self.name, personalized_response)
        
        return personalized_response

class DealerAgent(SimplifiedAgent):
    """Handles dealer related queries and human escalation"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="DealerAgent",
            system_message="""
You are the DealerAgent.

Your job is to handle complaints and issues raised by car dealers. If the user reports a missing payment, issue with an application, or any service delay:

1. Acknowledge the problem
2. Confirm a ticket has been created
3. Politely mention that you're transferring them to a human executive
4. End every response with: [final_answer]

Example:
"Thank you for your request. We have created a ticket. Please be online while we transfer your call to our executive. [final_answer]"
""",
            llm_config=llm_config,
            context=context
        )

    def generate_response(self, message: str) -> str:
        # You can customize here if needed
        enriched_message = f"This is a dealer assistant agent question. {message}"

        messages = [{"role": "user", "content": enriched_message}]
        response = self.agent.generate_reply(messages=messages)
        personalized_response = self.context.personalize(response)
        self.context.add_to_history(self.name, personalized_response)

        return personalized_response

    def _extract_info_from_message(self, message: str) -> None:
        """Extract and save dealer-related information from the message"""
        super()._extract_info_from_message(message)
        
        message_lower = message.lower()

        if any(word in message_lower for word in ["speak", "human", "person", "representative", "talk to"]):
            self.context.escalation_requested = True


class SmallTalkAgent(SimplifiedAgent):
    """Handles general conversation, greetings and farewells"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="SmallTalkAgent",
            system_message="""
You are the SmallTalkAgent. You handle general conversation and pleasantries.

Your responsibilities include:

1. Greeting users and making them feel welcome.
2. Asking for and remembering the user's name.
3. Handling thanks and acknowledgements.
4. Providing graceful conversations closings.
5. General chit-chat and rapport building.

Always be warm, friendly and conversational.
If you don't know the user's name yet, politely ask for it.
Use the user's name in response once you know it.
""",
            llm_config=llm_config,
            context=context
        )


def create_simplified_agents(llm_config: Dict[str, Any], context: ConversationContext, incentive_tool: Any):
    """Create all simplified agents"""
    return {
        "moderator": ModeratorAgent(llm_config, context),
        "pricing": PricingAgent(llm_config, context, incentive_tool),
        "policy": PolicyAgent(llm_config, context),
        "dealer": DealerAgent(llm_config, context),
        "smalltalk": SmallTalkAgent(llm_config, context)
    }