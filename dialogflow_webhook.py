from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shared.context import shared_context
from autogen_runner import start_autogen_conversation

app = FastAPI()

@app.post("/dialogflow-hook")
async def dialogflow_webhook(req: Request):
    body = await req.json()
    query_text = body["queryResult"]["queryText"]

    shared_context.update("last_user_input", query_text)

    # Get response from your AutoGen system
    final_response = await start_autogen_conversation(query_text)

    return JSONResponse({
        "fulfillmentText": final_response,
        "fulfillmentMessages": [
            {"text": {"text": [final_response]}},
            {"platform": "TELEPHONY", "telephonySynthesizeSpeech": {
                "ssml": f"<speak>{final_response}</speak>"}
            }
        ]
    })
