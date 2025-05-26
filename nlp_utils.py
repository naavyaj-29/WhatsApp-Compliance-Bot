import openai
from config import OPENAI_API
from models import load_side_effects

sideEffects = load_side_effects()

def simple(text):
    text = text.lower()
    compliance = None
    sideEffectFound = None
    for effect in sideEffects:
        if effect.lower() in text:
            sideEffectFound = effect
            break

    if any(word in text for word in ["yes","done", "given","administered"]):
        compliance = True
    elif any(word in text for word in ["no", "missed", "forgot"]):
        compliance = False
    return compliance, sideEffectFound
def gpt(text):
    if not OPENAI_API:
        return simple(text)
    openai.api_key = OPENAI_API
    prompt = ( f"Patient message: {text}\n" "Did the patient take medication today? (Yes / No / Unsure)\n" "Is there a mention of any side effects (list or 'none')? \n" "Short summary:")
    resp = openai.Completion.create(
        model = "text-davinci-003", prompt = prompt, maxTokens = 50, temp = 0)
    answer = resp.choices[0].text
    compliance = None
    if "yes" in answer.lower():
        compliance = True
    elif "no" in answer.lower():
        compliance = False
    sideEffectsFound = [effect for effect in sideEffects if effect.lower() in answer.lower()]
    return compliance, sideEffectsFound[0] if sideEffectsFound else None