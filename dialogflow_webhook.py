from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shared.context import shared_context
from autogen_runner import start_autogen_conversation
from main import chat_with_agents



app = FastAPI()

# @app.post("/dialogflow-hook")
# async def dialogflow_webhook(req: Request):
#     body = await req.json()
#     query_text = body["queryResult"]["queryText"]

#     shared_context.update("last_user_input", query_text)

#     # Get response from your AutoGen system
#     final_response = await start_autogen_conversation(query_text)

#     return JSONResponse({
#         "fulfillmentText": final_response,
#         "fulfillmentMessages": [
#             {"text": {"text": [final_response]}},
#             {"platform": "TELEPHONY", "telephonySynthesizeSpeech": {
#                 "ssml": f"<speak>{final_response}</speak>"}
#             }
#         ]
#     })


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    user_input = body["queryResult"]["queryText"]
    print(user_input)
    print(f"📩 User said: {user_input}")

    response = chat_with_agents(user_input)
    

    print(f"🤖 Bot says: {response}")

    return JSONResponse(content={
        "fulfillmentText": response
    })
