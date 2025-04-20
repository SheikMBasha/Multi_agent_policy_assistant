from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from shared.context import shared_context
from autogen_runner import start_autogen_conversation
import threading
from twilio.twiml.voice_response import VoiceResponse,Gather

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "✅ Server is alive"}

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


# Memory cache for responses (replace with Redis for prod)
response_cache = {}

@app.post("/twilio-voice-hook")
async def twilio_voice_hook(request: Request):
    twiml = VoiceResponse()

    gather = Gather(
        input="speech",
        action="/twilio-process-input",  # 👈 where to post speech result
        method="POST",
        timeout=10,
        speech_timeout="auto",
    )
    gather.say("Hi, how can I help you today?")
    twiml.append(gather)

    # Fallback if no input
    twiml.redirect("/twilio-voice-hook")

    return Response(content=str(twiml), media_type="application/xml")

@app.post("/twilio-process-input")
async def process_input(request: Request):
    form = await request.form()
    query_text = form.get("SpeechResult") or "Sorry, I didn't hear anything."

    # Now you can start background thread like before
    caller = form.get("From")
    shared_context.update("last_user_input", query_text)
    threading.Thread(target=handle_autogen_async, args=(caller, query_text), daemon=True).start()

    twiml = VoiceResponse()
    twiml.say("Sure, let me check that for you...")
    twiml.pause(length=4)
    twiml.redirect("/twilio-followup")
    return Response(content=str(twiml), media_type="application/xml")


@app.post("/twilio-followup")
async def twilio_followup(request: Request):
    form = await request.form()
    caller = form.get("From")

    final_response = response_cache.get(caller)

    twiml = VoiceResponse()
    if final_response:
        twiml.say(final_response)
        twiml.hangup()
        response_cache.pop(caller)  # ✅ remove only after use
    else:
        twiml.say("Still working on it. Please hold on...")
        twiml.pause(length=3)
        twiml.redirect("/twilio-followup")  # keep polling

    return Response(content=str(twiml), media_type="application/xml")



import asyncio

def handle_autogen_async(caller, query_text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_response = loop.run_until_complete(start_autogen_conversation(query_text))
        loop.close()

        print(f"✅ Agent reply for {caller}:\n{final_response}")
        response_cache[caller] = final_response or "Sorry, no response received."

    except Exception as e:
        print(f"❌ AutoGen error: {e}")
        response_cache[caller] = "There was an issue processing your request."

