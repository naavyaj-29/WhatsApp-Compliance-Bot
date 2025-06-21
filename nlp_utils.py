import openai
from models import load_side_effects
from config import TOGETHER_API_KEY
import json
import re
import together

sideEffects = [effect.lower() for effect in load_side_effects()]

COMPLIANCE_KEYWORDS = {
    "positive": ["yes", "done", "given", "administered", "applied", "used", "did it", "gave it", "gave the drops"],
    "negative": ["no", "missed", "forgot", "skipped", "not today", "didn’t", "did not", "couldn’t"]
}
HELP_KEYWORDS = [
    "help", "confused", "not sure", "don't know", "what to do", "need assistance", "worried", "scared",
    "talk to someone", "call me", "speak to doctor", "clinic", "emergency", "urgent", "panic", "afraid",
    "need support", "reach out", "not working", "problem", "issue"

]

def test_openai_key():
    try:
        together.api_key = TOGETHER_API_KEY
        models = together.Models.list()
        print("Together AI API key is valid. Models available:", [m["name"] for m in models["data"]])
    except Exception as e:
        print("OpenAI API key is invalid:", e)

def detect_intent(text):
    text = text.lower()
    for kw in HELP_KEYWORDS:
        if kw in text:
            return "help"
    return "normal"

def simple(text):
    text = text.lower()
    compliance = None
    side_effect = None

    for word in COMPLIANCE_KEYWORDS["positive"]:
        if word in text:
            compliance = True
            break
    
    for word in COMPLIANCE_KEYWORDS["negative"]:
        if word in text:
            compliance = False
            break

    for effect in sideEffects:
        if effect in text:
            side_effect = effect
            break
    return compliance, side_effect    

def gpt(user_message):
    together.api_key = TOGETHER_API_KEY
    prompt = f"""
You are an AI assistant checking if a patient took their eye drops. Here's the message they sent:

"{user_message}"

Please answer in JSON with the fields:
- "compliance": one of ["yes", "no", "partial", "unsure"]
- "sideEffect": one of ["none", "mild", "moderate", "severe", "unsure"]
- "reply": a short, friendly message that fits the user's tone and provides encouragement or next steps.

Respond only with JSON.
"""
    try:
        response = together.Complete.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            prompt=prompt.strip(),
            max_tokens=256,
            temperature=0.4,
            # stop=["\n\n", "\nPatient"]
        )

        print("=== GPT Debug ===")
        print("Raw response object:", json.dumps(response, indent=2))
        text = response['choices'][0]['text'].strip()
        print("Raw GPT output text:", repr(text))

        if not text:
            print("GPT returned empty response text.")
            return None, None, None

        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            json_str = match.group()
            print("Extracted JSON string:", json_str)
            parsed = json.loads(json_str)
            return parsed.get("compliance"), parsed.get("sideEffect"), parsed.get("reply")
        else:
            print("No JSON found in GPT output")
            return None, None, None

    except Exception as e:
        print("Together API error:", e)
        return None, None, None
