from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from shared.context import shared_context
from main import chat_with_agents
from twilio.twiml.voice_response import VoiceResponse, Gather
from fastapi.responses import PlainTextResponse




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

@app.post("/voice", response_class=PlainTextResponse)
async def voice(request: Request):
    form = await request.form()
    user_input = form.get("SpeechResult")

    response = VoiceResponse()

    if user_input:
        print("User said:", user_input)
        agent_reply = chat_with_agents(user_input)
        bot_reply = agent_reply.replace("[final_answer]", "").strip()
        print(f"Bot says: {bot_reply}")
        # Say the reply first
        response.say(bot_reply)


        # Then ask for the next input using <Gather> again
        gather = Gather(
            input="speech",
            timeout=5,
            speech_timeout="auto",
            action="/voice",
            method="POST"
        )

        response.append(gather)

        # Fallback if they say nothing
        response.say("I didn’t catch that. Thanks for calling!")
        response.hangup()

    else:
        # Initial interaction
        gather = Gather(
            input="speech",
            timeout=5,
            speech_timeout="auto",
            action="/voice",
            method="POST"
        )
        gather.say("Hey there, how can I assist you today?")
        response.append(gather)
        response.say("I didn’t hear anything. Goodbye.")
        response.hangup()

    return str(response)


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
