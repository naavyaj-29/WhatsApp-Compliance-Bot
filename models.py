import pandas as pd
from datetime import datetime
import os

data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

patients_csv = os.path.join(data_dir, "patients.csv")
appointments_csv = os.path.join(data_dir, "appointments.csv")
side_effects = os.path.join(data_dir, "side_effects.txt")
log_file = os.path.join(data_dir, "events.log")

def create_tables():
    if not os.path.exists(patients_csv):
        df = pd.DataFrame(columns=["phone", "name", "medication", "state"])
        df.to_csv(patients_csv, index=False)

    if not os.path.exists(appointments_csv):
        df = pd.DataFrame(columns=["phone", "appointment_time", "status"])
        df.to_csv(appointments_csv, index=False)

    if not os.path.exists(side_effects):
        with open(side_effects, "w") as f:
            f.write("vomiting\nseizure\nrash\nhigh fever\nfainting\n")
def connect_db():
    pass
def load_patients():
    patients = pd.read_csv(patients_csv, dtype={'phone': str})
    return patients
def save_patients(df):
    df.to_csv(patients_csv, index=False)
def load_appointments():
    return pd.read_csv(appointments_csv)

def save_appointments(df):
    df.to_csv(appointments_csv, index=False)
def load_side_effects():
    with open(side_effects) as f:
        return [l.strip() for l in f if l.strip()]
def checkSevereSideEffects(effect_text):
    effects = load_side_effects()
    for effect in effects:
        if effect in effect_text.lower():
            return True
    return False
def log_Event(phone, event_type, msg):
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}, {phone}, {event_type}, {msg}\n")

def getUser(phone):
    df = load_patients() 
    df.columns = df.columns.str.strip().str.lower()
    print("Normalized columns:", df.columns.tolist()) 
    row = df[df["phone"] == phone]
    if row.empty:
        return None
    return row.iloc[0].to_dict()
def setUserState(phone, new_state):
    df = load_patients()
    df.columns = [col.lower().strip() for col in df.columns]
    phone = phone.strip().lstrip('+')
    df['phone'] = df['phone'].astype(str).str.strip().str.replace('+', '')

    if 'state' not in df.columns:
        df['state'] = ""
    df['state'] = df['state'].astype(str)
    df.loc[df['phone'] == phone, 'state'] = new_state
    df.to_csv(patients_csv, index=False)
    df['state'] = df['state'].fillna("").astype(str)



def getComplianceTrends():
    import pandas as pd
    log_File = os.path.join(data_dir, "events.log")
    if not os.path.exists(log_File):
        return pd.DataFrame()
    
    logs = []
    with open(log_File) as f:
        for line in f:
            dt, phone, etype, msg = line.strip().split(",", 3)
            logs.append({"datetime": dt[:10], "phone": phone, "type": etype})
    df = pd.DataFrame(logs)
    if df.empty:
        return pd.DataFrame()
    df['datetime'] = pd.to_datetime(df['datetime'])
    grouped = df[df['type'].isin(['compliance', 'noncompliance'])].groupby(['datetime', 'type']).size().unstack(fill_value=0)
    return grouped.reset_index()
