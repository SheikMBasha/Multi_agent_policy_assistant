"""SmallTalk agent implementation for handling general conversation"""

from typing import Dict, Any
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext

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