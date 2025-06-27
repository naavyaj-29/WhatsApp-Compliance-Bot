# AI-Powered Assistant for Medication Adherence

A WhatsApp-based healthcare assistant that aims to monitor medication compliance and side effects, while creating ease of communication with patients and clinicians using Twilio, Flask, and GPT-based NLP.

## Overview

This MVP enables:

- Medication reminders through WhatsApp
- Patient compliance tracking through natural language responses
- Side effect detection including flagging and alerts for severe symptoms
- Appointment reminders sent automatically
- Clinician alerts for critical cases

## Features

- Twilio WhatsApp Integration: Sends and receives patient messages.
- GPT NLP: Extracts information about compliance and side effects from unstructured replies.
- Event Logging: Tracks compliance, side effects, and critical events.
- Scheduled Messaging: Uses `APScheduler` to automate medication reminders and appointment messages.
- Clinician Alerting: Detects severe symptoms and prints a notification (extendable to email/text).

## Project Structure

app.py # Flask app and Twilio webhook endpoint
models.py # Utility functions: load_patients load_appointments, log_Event
nlp_utils.py # GPT-based NLP logic for compliance/side effects
config.py # Twilio config values (SID, token, etc.)
.env # Environment variables (Twilio credentials, etc.)
requirements.txt # Python dependencies


## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/your-username/atropine-bot.git
   cd atropine-bot

2. Install dependencies
    pip install -r requirements.txt

3. Set up environment variables for:
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_WHATSAPP_FROM

4. Start the Flask app
    python app.py

5. Expose locally using ngrok for Twilio testing
    ngrok http 5000

6. Set your Twilio webhook URL
    https://<your-ngrok-id>.ngrok.io/bot
    

