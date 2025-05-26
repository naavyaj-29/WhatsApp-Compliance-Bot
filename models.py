import pandas as pd
from datetime import datetime
import os

data_dir = os.path.join(os.path.dirname(__file__), "data")

patients_csv = os.path.join(data_dir, "patients.csv")
appointments_csv = os.path.join(data_dir, "appointments.csv")
side_effects = os.path.join(data_dir, "side_effects.txt")

def load_patients():
    return pd.read_csv(patients_csv)
def save_patients(df):
    df.to_csv(patients_csv, index=False)
def load_appointments():
    return pd.read_csv(appointments_csv)

def save_appointments(df):
    df.to_csv(appointments_csv, index=False)
def load_side_effects():
    with open(side_effects) as f:
        return [l.strip() for l in f if l.strip()]
def log_Event(phone, event_type, msg):
    log_file = os.path.join(data_dir, "events.log")
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}, {phone}, {event_type}, {msg}\n")

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
