from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from models import load_patients, log_Event, load_appointments
from nlp_utils import gpt
import pandas as pd
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import time
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

app = Flask(__name__)
patient_responses = {}
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

def getPatient(phone):
    patients = load_patients()
    patients.columns = [col.lower().strip() for col in patients.columns]
    match = patients[patients['phone'] == phone]
    if not match.empty:
        return match.iloc[0]
    return None

def alertClinician(phone, message):
    print(f"Severe side effect reported by {phone}: {message}")

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body','').strip()
    fromNumber = request.values.get('From', '')
    phone = fromNumber.replace("whatsapp:", "")
    patient = getPatient(phone)

    resp = MessagingResponse()
    msg = resp.message()

    if not patient:
        msg.body("Sorry, your number appears to not be in our system")
        return str(resp)
    compliance, sideEffect = gpt(incoming_msg)

    patient_responses[phone] = {
        'last_response': incoming_msg,
        'timestamp': datetime.datetime.now()
    }
    if sideEffect and checkSevereSideEffects(sideEffect):
        log_Event(phone, "severe side effect", sideEffect)
        msg.body("This may require urgent care. A clinician will contact you. ")
        alertClinician(phone, sideEffect)
        return str(resp)
    if compliance is not None:
        log_Event(phone, "compliance" if compliance else "noncompliance", incoming_msg)
        msg.body("Thanks for confirming!" if compliance else "Thanks. Please try to follow instructions.")
        msg.body("Did you notice any side effects?")
    elif sideEffect:
        log_Event(phone, "side effect", sideEffect)
        msg.body(f"Thanks for reporting: {sideEffect}. A clinician will review it soon.")
    else:
        msg.body("Thank you for your message. Please reply  'yes' if the medication was administered, 'no' if missed. Please describe any side effects")
    return str(resp)


def sendReminder():
    patients = load_patients()
    for _, patient in patients.iterrows():
        patients.columns = [col.lower().strip() for col in patients.columns]
        phone = patient['phone']
        message = "This is your daily reminder to administer atropine eye drops! Please reply 'yes' if done, 'no' if not. "
        client.messages.create(body = message, from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}")

def sendCheckIn():
    patients = load_patients()
    for _, patient in patients.iterrows():
        patients.columns = [col.lower().strip() for col in patients.columns]
        phone = patient['phone']
        message = "This a weekly check-in: did you administer medication this week? Did you notice any side effects? "
        client.messages.create(body = message, from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}")

def sendAppointmentReminders():
    appointments = load_appointments()
    today = datetime.date.today()
    upcoming = appointments[appointments['date'] == str(today + datetime.timedelta(days=1))]
    for _, appt in upcoming.iterrows():
        phone = appt['phone']
        msg = f"Reminder: You have an appointment tomorrow at {appt['time']}."
        client.messages.create(body=msg, from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}")
def checkSevereSideEffects(text):
    critical = ['vision loss', 'blurred vision', 'sever pain', 'swelling']
    return any(word in text.lower() for word in critical)

scheduler.add_job(sendAppointmentReminders, 'cron', hour=12)  
scheduler.add_job(sendReminder, 'cron', hour=20, minute=0)
scheduler.add_job(sendCheckIn, 'cron', day_of_week ='fri', hour=18, minute=0)

if __name__ == '__main__':
    app.run(port=5000)
