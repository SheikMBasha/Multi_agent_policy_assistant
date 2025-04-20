from twilio.rest import Client

account_sid = ''
auth_token = ''
twilio_number = '+17015589132'  # Twilio number
to_number = '+918441015566'  # Your phone number

client = Client(account_sid, auth_token)

call = client.calls.create(
    to=to_number,
    from_=twilio_number,
    url="https://42e9-2405-201-c404-8812-a9b6-ccc7-dbb7-189d.ngrok-free.app/voice"
)

print(f"Call initiated. SID: {call.sid}")
