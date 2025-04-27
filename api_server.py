# api_server.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time

# Import your agent system
from config.llm_config import get_llm_config
from config.system_config import get_system_config
from context.conversation_context import ConversationContext
from agents import create_agents
from tools.calculateincentivetool import CalculateIncentiveTool

# Initialize your agent system
context = ConversationContext()
llm_config = get_llm_config()
system_config = get_system_config()
incentive_tool = CalculateIncentiveTool(api_url="http://localhost:8000/calculate-compensation")
agents = create_agents(llm_config, context, incentive_tool)

app = FastAPI(title="Automotive Assistant API")

class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class MessageResponse(BaseModel):
    agent: str
    response: str
    context: Dict[str, Any]
    response_time_ms: float

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    # Start the timer
    start_time = time.time()
    
    try:
        # Process the message
        user_message = request.message
        
        # Add to history
        context.add_to_history("User", user_message)
        
        # Special handling for getting the user's name
        if not context.user_name:
            name = context.extract_name(user_message)
            if name:
                context.user_name = name
                response = f"Nice to meet you, {name}! How can I help you with your automotive needs today?"
                # Calculate elapsed time in milliseconds
                elapsed_time_ms = (time.time() - start_time) * 1000
                return {
                    "agent": "SmallTalkAgent", 
                    "response": response, 
                    "context": {"user_name": name},
                    "response_time_ms": elapsed_time_ms
                }
            else:
                response = "I didn't catch your name. Could you please tell me your name?"
                # Calculate elapsed time in milliseconds
                elapsed_time_ms = (time.time() - start_time) * 1000
                return {
                    "agent": "SmallTalkAgent", 
                    "response": response, 
                    "context": {},
                    "response_time_ms": elapsed_time_ms
                }
        
        # Handle thanks message
        if any(thank_you in user_message.lower() for thank_you in ["thank you", "thanks"]):
            response = "You're very welcome! Is there anything else I can assist you with?"
            # Calculate elapsed time in milliseconds
            elapsed_time_ms = (time.time() - start_time) * 1000
            return {
                "agent": "SmallTalkAgent", 
                "response": response, 
                "context": {"user_name": context.user_name},
                "response_time_ms": elapsed_time_ms
            }
        
        # Ask the moderator to determine which agent should handle this
        selected_agent_name = agents["moderator"].determine_agent(user_message)
        
        # Convert display name to internal key
        agent_mapping = {
            "PricingAgent": "pricing",
            "PolicyAgent": "policy", 
            "DealerAgent": "dealer",
            "SmallTalkAgent": "smalltalk"
        }
        agent_key = agent_mapping.get(selected_agent_name, "smalltalk")
        
        # Get the response from the selected agent
        response = agents[agent_key].generate_response(user_message)
        
        # Return response with context info
        context_info = {
            "user_name": context.user_name,
            "turns_count": context.turns_count
        }
        
        # Calculate elapsed time in milliseconds
        elapsed_time_ms = (time.time() - start_time) * 1000
        print(f"Elapsed time is {elapsed_time_ms}")
        return {
            "agent": selected_agent_name,
            "response": response,
            "context": context_info,
            "response_time_ms": elapsed_time_ms
        }
        
    except Exception as e:
        # Calculate elapsed time even for errors
        elapsed_time_ms = (time.time() - start_time) * 1000
        raise HTTPException(status_code=500, detail=f"Error ({elapsed_time_ms:.2f}ms): {str(e)}")

@app.get("/")
async def root():
    return {"message": "Automotive Assistant API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)