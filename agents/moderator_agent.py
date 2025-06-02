"""Moderator agent implementation for routing queries to specialized agents"""

import traceback
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import re
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext

# Import embedding model - you'll need to choose one:
# Option 1: Using sentence-transformers (recommended)
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')  # Small, fast model
except ImportError:
    # For fallback, we'll use a simpler approach
    EMBEDDING_MODEL = None
    print("Warning: sentence-transformers not installed. Using fallback embedding method.")

class ModeratorAgent(SimplifiedAgent):
    """Determines which specialist agent should handle the query and filters inappropriate content"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="ModeratorAgent",
            system_message="""
You are the RouterAgent for a dealer voice assistant. Based on the user query, You determine which agent should respond to the user query.

- @PricingAgent: Calculates the dealer compensation based on dealer name. It is the agent which will return the final answer.
- @PolicyAgent: Use if the user is asking about loan policies, rules, required documents, eligibility, term length, maximum age, conditions, or approval criteria.
- @DealerAgent: Use if the user wants to log a complaint, report an issue, or give feedback about the dealership experience.

DO NOT respond or explain — just tag the appropriate agent with the full user query.

Examples:
- "What documents do I need?" → PolicyAgent
- "What's the current APR on a hatchback?" → PricingAgent
- "The dealer was rude to me" → DealerAgent
- "What is the loan term length?" → PolicyAgent
- "Dealership or Dealer is or Dealership Name is or Dealer Name is: " -> PricingAgent
# Be Precise and respond with ONLY the agent name.
            """,
            llm_config=llm_config,
            context=context
        )
        
        # Initialize content categories and examples
        self.content_categories = {
            "automotive": [
                        # Add more specific loan-related examples
                "What are the chances of my loan being approved?",
                "What are the odds of loan approval?",
                "How likely am I to get approved for financing?",
                "Can you tell me about loan approval likelihood?",
                "What's the probability of getting a car loan?",
                "What's the approval rate for auto loans?",
                "Do I qualify for a car loan?",
                "What credit score do I need for loan approval?",
                "What factors affect my loan approval chances?",
                "How can I improve my chances of loan approval?",
                "What's the dealer incentive at Prestige Motors?",
                "Can you tell me about financing options?",
                "What's the warranty policy?",
                "How much is the APR for a vehicle loan?",
                "Tell me about pricing at Sonic Automotive",
                "What documents do I need for a car loan?",
                "Is this dealership offering any special rates?",
                "What's the down payment requirement?",
                "How long is the loan term?",
                "What credit score do I need for approval?",
                "When can I pick up my car?",
                "Do you offer extended warranties?",
                "What's the difference between leasing and financing?",
                "How does the trade-in process work?",
                "Can I get pre-approved for a car loan?"
            ],
            "off_topic": [
                # Make weather examples more prominent
                "What is the weather today?",
                "What's the forecast for tomorrow?",
                "Is it going to rain?",
                "How hot is it outside?",
                "Will it snow this weekend?",
                "Tell me a joke",
                "What's the weather like?",
                "Can you sing a song?",
                "Tell me about politics",
                "Write a poem",
                "How old are you?",
                "Do you like pizza?",
                "Who created you?",
                "What's your favorite color?",
                "Tell me a story",
                "I'm bored, entertain me",
                "What do you think about life?",
                "What's your name?",
                "Do you have feelings?",
                "Tell me about yourself"
            ],
            "illegal": [
                "How can I rob a bank?",
                "Can you help me hack a system?",
                "How to steal a car?",
                "Ways to cheat on taxes",
                "How to forge documents?",
                "How can I commit fraud?",
                "Can you help me avoid paying taxes?",
                "How to break into a house?",
                "Ways to smuggle illegal goods",
                "How to fake my identity?"
            ],
            "harmful": [
                "How to hurt myself?",
                "Easiest way to die",
                "How to make a weapon?",
                "Ways to harm others",
                "Dangerous pranks to try",
                "How to make someone sick?",
                "What poisons are untraceable?",
                "How to make someone suffer?",
                "Ways to cause an accident",
                "How to get revenge on someone?"
            ],
        }
        
        # Generate embeddings for each category's examples
        self.category_embeddings = self._initialize_embeddings()

    def _initialize_embeddings(self) -> Dict[str, np.ndarray]:
        """Initialize embeddings for content categories"""
        category_embeddings = {}
        
        # If we have a proper embedding model
        if EMBEDDING_MODEL is not None:
            for category, examples in self.content_categories.items():
                # Get embeddings for all examples in this category
                try:
                    embeddings = EMBEDDING_MODEL.encode(examples)
                    # Average the embeddings to get a category centroid
                    category_embeddings[category] = np.mean(embeddings, axis=0)
                except Exception as e:
                    print(f"Error creating embeddings for {category}: {e}")
                    # Fallback to empty embedding if error occurs
                    category_embeddings[category] = np.zeros(384)  # Default MiniLM dimension
        else:
            # Fallback for when no embedding model is available
            # This is a simplified approach using word overlap
            print("Using word-based fallback for content categorization")
            for category, examples in self.content_categories.items():
                # Create a "bag of words" for each category
                words = []
                for example in examples:
                    words.extend(re.findall(r'\b\w+\b', example.lower()))
                category_embeddings[category] = set(words)
        
        return category_embeddings

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if np.all(a == 0) or np.all(b == 0):
            return 0.0
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _word_similarity(self, message: str, category_words: set) -> float:
        """Calculate word overlap similarity for fallback method"""
        message_words = set(re.findall(r'\b\w+\b', message.lower()))
        if not message_words:
            return 0.0
        
        # Calculate Jaccard similarity: intersection over union
        intersection = message_words.intersection(category_words)
        union = message_words.union(category_words)
        
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def classify_content(self, message: str) -> Tuple[bool, str]:
        """
        Classify a message into appropriate or inappropriate category
        
        Args:
            message: The user message to classify
            
        Returns:
            Tuple of (is_inappropriate, category)
        """
        # Using embedding model if available
        if EMBEDDING_MODEL is not None:
            try:
                # Get embedding for the message
                message_embedding = EMBEDDING_MODEL.encode(message)
                
                # Find similarities to each category
                similarities = {
                    category: self._cosine_similarity(message_embedding, embedding)
                    for category, embedding in self.category_embeddings.items()
                }

                # Debug logging - this helps see why things are being misclassified
                print("Content classification scores:")
                for category, score in similarities.items():
                    print(f"  - {category}: {score:.4f}")
                
                # Find the highest similarity category
                best_category = max(similarities.items(), key=lambda x: x[1])
                category, similarity = best_category
                
                # Increase threshold for off-topic determination
                # This makes the system less sensitive to marking things as off-topic
                if category == "off_topic" and similarity < 0.45:
                    print(f"Off-topic similarity {similarity:.4f} below threshold 0.45, treating as automotive")
                    return False, "automotive"
            
                # Increase threshold for illegal determination
                # This makes the system less sensitive to marking things as illegal
                if category == "illegal" and similarity < 0.40:
                    print(f"Illegal similarity {similarity:.4f} below threshold 0.40, treating as automotive")
                    return False, "automotive"
            
                # Increase threshold for harmful determination
                if category == "harmful" and similarity < 0.40:
                    print(f"Harmful similarity {similarity:.4f} below threshold 0.40, treating as automotive")
                    return False, "automotive"
            
                # Special handling for weather-related queries
                if any(weather_term in message.lower() for weather_term in ["weather", "forecast", "rain", "sunny", "temperature"]):
                    print("Weather-related term detected, marking as off-topic")
                    return True, "off_topic"
                
                # If it's automotive, we need a reasonable threshold too
                if category == "automotive" and similarity < 0.25:
                    # If very low similarity to all categories, check for common off-topic triggers
                    if any(term in message.lower() for term in ["joke", "song", "weather", "politics", "news", "game"]):
                        print(f"Low automotive similarity but detected off-topic term, marking as off-topic")
                        return True, "off_topic"
            
                # If it's not automotive, it's inappropriate
                if category != "automotive":
                    return True, category
            
                return False, "automotive"
            
            except Exception as e:
                print(f"Error in embedding classification: {e}")
                # Fall back to keyword approach if embeddings fail
        
        # Fallback word-based method
        similarities = {}
        for category, word_set in self.category_embeddings.items():
            if isinstance(word_set, set):
                similarities[category] = self._word_similarity(message, word_set)
            else:
                # Skip if we somehow have non-set in fallback mode
                similarities[category] = 0.0
        
        # Find highest similarity
        best_category = max(similarities.items(), key=lambda x: x[1])
        category, similarity = best_category
        
        # If similarity is too low, default to automotive
        if similarity < 0.1:
            return False, "automotive"
        
        # If not automotive, it's inappropriate
        if category != "automotive":
            return True, category
        
        return False, "automotive"

    def get_inappropriate_response(self, message: str, category: str = "") -> str:
        """
        Generate a context-aware response for inappropriate content
        
        Args:
            message: Original inappropriate message
            category: Category of inappropriateness
            
        Returns:
            Appropriate deflection response
        """
        # Context-aware responses based on category
        responses = {
            "off_topic": "I'm your automotive assistant focused on helping with vehicle policies, prices, and dealer information. I'm not designed to handle that type of request. How can I assist you with your automotive needs today?",
            
            "illegal": "I'm programmed to assist with automotive questions. I can't provide information about activities that might be illegal. If you have questions about vehicle policies or pricing, I'm happy to help with those instead.",
            
            "harmful": "I'm designed to provide automotive information. For your well-being, I'd suggest speaking with a qualified professional about that topic. Can I help you with any automotive questions instead?",
            
            # Default response for when category isn't specified
            "default": "I'm designed to assist with automotive-related information such as dealer details, pricing, and policies. I'd be happy to help you with those topics instead. What automotive information can I provide for you today?"
        }
        
        return responses.get(category, responses["default"])

    def determine_agent(self, message: str) -> Tuple[str, Optional[str]]:
        """
        Determine which agent should handle the message and check for inappropriate content
        
        Args:
            message: User message to route
            
        Returns:
            Tuple of (agent_name, inappropriate_category or None)
        """
        # Check for explicit off-topic keywords first
        message_lower = message.lower()
    
        # Common weather-related queries
        if any(term in message_lower for term in ["weather", "forecast", "temperature", "rain", "sunny", "cloudy", "storm"]):
            return "SmallTalkAgent", "off_topic"
    
        # Common entertainment requests
        if any(term in message_lower for term in ["joke", "funny", "tell me a story", "sing", "game", "play"]):
            return "SmallTalkAgent", "off_topic"
        
        # First check if message is inappropriate
        is_inappropriate, category = self.classify_content(message)
        
        if is_inappropriate:
            # Return SmallTalkAgent with the inappropriate category
            return "SmallTalkAgent", category
        
        # If message is appropriate, continue with normal agent determination
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
                    return agent, None
                    
            return "SmallTalkAgent", None
        except Exception as e:
            print(f"DETAILED ERROR in moderator agent: {type(e)}, {e}")
            print(traceback.format_exc())
            
            # Temporary fallback
            if "loan" in message.lower():
                return "PricingAgent", None
            return "SmallTalkAgent", None