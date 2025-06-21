from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from models import load_patients, log_Event, load_appointments
from nlp_utils import gpt, simple, detect_intent
from models import (connect_db, create_tables, checkSevereSideEffects, log_Event, getUser, setUserState,)
import pandas as pd
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import time
import re
from nlp_utils import test_openai_key
from flask import Response
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

app = Flask(__name__)
connect_db()
create_tables()

patient_responses = {}
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

side_effect_map = {
    "1": "Eye redness/itchiness",
    "2": "Light sensitivity",
    "3": "Blurred vision",
    "4": "None of the above"
}

def getPatient(phone):
    patients = load_patients()
    patients.columns = [col.lower().strip() for col in patients.columns]
    phone = phone.strip()
    if phone.startswith('+'):
        phone = phone[1:]

    patients['phone'] = patients['phone'].astype(str).str.strip().str.replace('+', '')

    print(f"Incoming phone (from WhatsApp): {phone}")
    print(f"Patient phone list:\n{patients['phone'].tolist()}")

    match = patients[patients['phone'] == phone]
    if not match.empty:
        return match.iloc[0]
    return None

def alertClinician(phone, message):
    print(f"Severe side effect reported by {phone}: {message}")

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body','').strip().lower()
    fromNumber = request.values.get('From', '')
    phone = fromNumber.replace("whatsapp:", "").lstrip("+")
    patient = getPatient(phone)

    resp = MessagingResponse()
    msg = resp.message()
    print(f"Message received: {incoming_msg} from {phone}")

    if patient is None:
        msg.body("You are not currently enrolled in the atropine monitoring system. Please contact your clinic.")
        print("Responding with:", str(resp))
        return Response(str(resp), mimetype="application/xml")

    compliance, sideEffect, reply = gpt(incoming_msg)
    if compliance is None and sideEffect is None:
        print("Calling Simple NLP for message:", incoming_msg)
        compliance, sideEffect = simple(incoming_msg)
        print(f"Fallback returned compliance={compliance}, sideEffect={sideEffect}")
   
    if sideEffect:
        log_Event(phone, "side effect", incoming_msg)
        if checkSevereSideEffects(sideEffect):
            log_Event(phone, "severe side effect", sideEffect)
            msg.body("This may require urgent care. A clinician will contact you shortly.")
            alertClinician(phone, sideEffect)
        else:
            if sideEffect=='moderate' or sideEffect=='mild':
                msg.body("Thanks for reporting the side effect. We will continue monitoring and reach out, if needed.")
            else:
                msg.body(reply)
        return Response(str(resp), mimetype="application/xml")

    if compliance is not None:
        event_type = "compliance" if compliance else "noncompliance"
        log_Event(phone, event_type, incoming_msg)
        if compliance:
            msg.body("Thanks for confirming you gave the medication and for supporting the treatment.")
        else:
            msg.body("Thanks for letting us know. Please try to follow the schedule as your clinic suggested.")
        return Response(str(resp), mimetype="application/xml")

    intent = detect_intent(incoming_msg)
    if intent =="help":
        msg.body("It sounds like you need support. A clinic staff member will reach out to you shortly. If it's urgent, please contact the clinic directly.")
        log_Event(phone, "help_requested", incoming_msg)
        alertClinician(phone, "User is asking for help or is confused.")
        print("Responding with:", str(resp))
        return Response(str(resp), mimetype="application/xml")

    user_state = (getUser(phone) or {}).get("state", "")
    user_state = getUser(phone).get("state", "")

    if user_state == "reschedule_pending":
        if incoming_msg in ["yes", "yeah", "yup", "sure"]:
            msg.body("Thanks! We'll contact you to reschedule your appointment.")
            log_Event(phone, "reschedule_confirmed", incoming_msg)
            setUserState(phone, "") 
            print("Responding with:", str(resp))
            return Response(str(resp), mimetype="application/xml")
        elif incoming_msg in ["no", "nope", "not now"]:
            msg.body("Okay, we'll keep your current appointment as scheduled.")
            log_Event(phone, "reschedule_declined", incoming_msg)
            setUserState(phone, "")
            print("Responding with:", str(resp))
            return Response(str(resp), mimetype="application/xml")
    if "reschedule" in incoming_msg or "change" in incoming_msg:
        msg.body("Would you like to reschedule your appointment? Reply: Yes or No")
        setUserState(phone, "reschedule_pending")
        log_Event(phone, "reschedule_prompted", incoming_msg)
        print("Responding with:", str(resp))
        return Response(str(resp), mimetype="application/xml")
    

    if any(kw in incoming_msg for kw in ["medication", "drops", "atropine", "medicine"]):
        msg.body("Did you give the medication today? Please reply Yes or No.")
        setUserState(phone, "awaiting_medication_confirmation")
        log_Event(phone, "medication_prompted", incoming_msg)
        print("Responding with:", str(resp))
        return Response(str(resp), mimetype="application/xml")
    
    
    #medical context
    if user_state == "awaiting_medication_confirmation":
        if incoming_msg in ["yes", "yeah", "yup", "sure"]:
            msg.body("Thanks for confirming you gave the medication and for supporting the treatment.")
            log_Event(phone, "compliance", incoming_msg)
            setUserState(phone, "")
            print("Responding with:", str(resp))
            return Response(str(resp), mimetype="application/xml")
        elif incoming_msg in ["no", "nope", "not yet", "not today"]:
            msg.body("Thanks for letting us know. Please try to follow the schedule as your clinic suggested.")
            log_Event(phone, "noncompliance", incoming_msg)
            setUserState(phone, "")
            print("Responding with:", str(resp))
            return Response(str(resp), mimetype="application/xml")
        else:
            msg.body("Please reply Yes or No regarding medication.")
            print("Responding with:", str(resp))
            return Response(str(resp), mimetype="application/xml")

    if incoming_msg in ["yes", "no"]:
        msg.body("Please clarify if your message refers to medication or side effects, or ask a question.")
        print("Responding with:", str(resp))
        return Response(str(resp), mimetype="application/xml")
    
    if reply:
        msg.body(reply)
    else:
        msg.body("I'm here to help! Can you clarify if you gave the medication or noticed any side effects?")
    log_Event(phone, "unclassified", incoming_msg)
    return Response(str(resp), mimetype="application/xml")


    # if compliance is None and sideEffect is None:
    #     msg.body("Sorry, I couldn't understand that. Could you clarify whether you gave the medication and noticed any symptoms?")
    # return str(resp)

def sendReminder():
    patients = load_patients()
    patients.columns = [col.lower().strip() for col in patients.columns]
    for _, patient in patients.iterrows():
        phone = patient['phone']
        message = "This is your daily reminder to administer atropine eye drops! Please reply 'yes' if done, 'no' if not. "
        client.messages.create(body = message, from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}")

def sendCheckIn():
    print("working")
    patients = load_patients()
    patients.columns = [col.lower().strip() for col in patients.columns]
    for _, patient in patients.iterrows():
        phone = patient['phone']
        message = (
            "Weekly check-in: Have you noticed any of the following side effects?\n"
            "1) Eye redness/itchiness\n"
            "2) Light sensitivity\n"
            "3) Blurred vision\n"
            "4) None of the above\n"
            "Reply with the number(s)."
        )
        client.messages.create(body = message, from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}")

def sendAppointmentReminders():
    appointments = load_appointments()
    today = datetime.date.today()
    upcoming = appointments[appointments['date'] == str(today + datetime.timedelta(days=2))]
    for _, appt in upcoming.iterrows():
        phone = appt['phone']
        time = appt['time']
        date = appt['date']
        msg = f"Reminder: You have an appointment {time} on {date}. Would you like to reschedule? Reply: Yes / No"
        client.messages.create(body=msg, from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}")

severeSideEffects = [
    r'vision\s*loss', r'blurr?ed?\s*vision', r'severe\s*pain', r'swelling',
    r'eye\s*infection', r'light\s*sensitivity', r'severe\s*headache',
    r'difficulty\s*breathing', r'facial\s*swelling', r'eye\s*redness\s*with\s*pain',
    r'eye\s*pain\s*with\s*discharge'
]
def checkSevereSideEffects(text):
    print("checking...")
    text = text.lower()
    for pattern in severeSideEffects:
        if re.search(pattern, text):
            return True
    return False

test_openai_key()
scheduler.add_job(sendReminder, 'cron', day_of_week='mon', hour=20, minute=0)
scheduler.add_job(sendCheckIn, 'cron', day_of_week='wed', hour=23, minute=34)
scheduler.add_job(sendAppointmentReminders, 'cron', hour=12)  

if __name__ == '__main__':
    app.run(port=5000)
