import openai
from config import OPENAI_API
from models import load_side_effects
import json
import re

sideEffects = [effect.lower() for effect in load_side_effects()]
openai.api_key = OPENAI_API

COMPLIANCE_KEYWORDS = {
    "positive": ["yes", "done", "given", "administered", "applied", "used", "did it", "gave it", "gave the drops"],
    "negative": ["no", "missed", "forgot", "skipped", "not today", "didn’t", "did not", "couldn’t"]
}
HELP_KEYWORDS = [
    "help", "confused", "not sure", "don't know", "what to do", "need assistance", "worried", "scared",
    "talk to someone", "call me", "speak to doctor", "clinic", "emergency", "urgent", "panic", "afraid",
    "need support", "reach out", "not working", "problem", "issue"

]
def detect_intent(text):
    text = text.lower()
    for kw in HELP_KEYWORDS:
        if kw in text:
            return "help"
    return None

def simple(text):
    text = text.lower()
    compliance = None
    sideEffectFound = None

    if any(kw in text for kw in COMPLIANCE_KEYWORDS["positive"]):
        compliance = True
    elif any(kw in text for kw in COMPLIANCE_KEYWORDS["negative"]):
        compliance = False

    for effect in sideEffects:
        if effect in text:
            sideEffectFound = effect
            break

    return compliance, sideEffectFound

def parse_gpt_response(content):
    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in GPT response")
        data = json.loads(match.group(0))

        compliance_map = {
            "yes":True,
            "no":False,
            "unsure":None
        }
        compliance_raw = data.get("compliance", "").strip().lower()
        compliance = compliance_map.get(compliance_raw, None)

        side_effect_found = None
        if isinstance(data.get("side_effects"), list):
            for effect in data["side_effects"]:
                if effect.lower() in sideEffects:
                    side_effect_found = effect.lower()
                    break
        return compliance, side_effect_found
    except Exception as e:
        print(f"Error parsing GPT response: {e}")
        return None, None
    

def gpt(text):
    if not OPENAI_API:
        return simple(text)
    prompt = f"""
You are an AI assistant helping a clinic monitor atropine eye drop therapy for pediatric patients.
Given the caregiver message below, determine:

1. Whether the medication was administered (compliance).
2. If any known side effects were reported (you will be provided a list).

Message: "{text}"

Known side effects: {sideEffects}

Respond in this exact JSON format:
{{
  "compliance": "yes" | "no" | "unsure",
  "side_effects": ["effect1", "effect2"] or []
}}
"""
    try:
        response = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": "You extract compliance and symptoms from caregiver messages."},
                {"role": "user", "content": prompt}
            ],
            temperature =0
        )
        content = response['choices'][0]['message']['content']
        print("raw output: ", content)
        return parse_gpt_response(content)
    except Exception as e:
        print(f"GPT call failed: {e}")
        return None, None
    


