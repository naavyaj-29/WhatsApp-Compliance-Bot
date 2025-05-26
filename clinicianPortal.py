from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
from models import load_patients, save_patients, log_Event, load_appointments, save_appointments
from config import ADMIN_PASSWORD
import os
from models import getComplianceTrends
from flask import send_file
from io import BytesIO
from clinicianPortal import generateComplianceReport as generateReport

data_dir = os.path.join(os.path.dirname(__file__), "data")

app = Flask(__name__)
app.secret_key = "turmerik"

@app.route("/", methods=['GET', 'POST'])
def dashboard():
    if request.method =='POST':
        pw = request.form.get("password")
        if pw!= ADMIN_PASSWORD:
            flash("Incorrect!")
            return redirect(url_for('dashboard'))
    patients = load_patients()
    appointments = load_appointments()
    trends = getComplianceTrends()

    chart = {"labels": trends['datetime'].dt.strftime('%Y-%m-%d').tolist(),
        "compliance": trends.get('compliance', pd.Series()).fillna(0).astype(int).tolist(),
        "noncompliance": trends.get('noncompliance', pd.Series()).fillna(0).astype(int).tolist()
    }

    return render_template("dashboard.html", patients = patients.to_dict("records"), appointments = appointments.to_dict("records"), chart_data = chart)

@app.route("/upload_patients", methods=['GET', 'POST'])
def upload_patients():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            df = pd.read_csv(file)
            save_patients(df)
            flash("Patient list updated")
            return redirect(url_for('dashboard'))
    return render_template("upload.html")
@app.route("/alerts")
def alerts():
    logFile = "data/events.log"
    alerts = []
    if os.path.exists(logFile):
        with open(logFile) as f:
            for line in f:
                dt, phone, etype, msg = line.strip().split(",",3)
                if etype in ["sideEffect", "noncompliance"]:
                    alerts.append({"datetime":dt, "phone":phone, "type":etype, "msg": msg})
    return render_template("alerts.html", alerts = alerts)
def generateComplianceReport():
    import pandas as pd
    log_file = os.path.join(data_dir, "events.log")
    patients = load_patients()
    if not os.path.exists(log_file):
        return pd.DataFrame()
    
    logs =[]
    with open(log_file) as f:
        for line in f:
            dt, phone, etype, msg = line.strip().split(",", 3)
            logs.append({"datetime":dt, "phone":phone, "type": etype, "msg":msg})
    df = pd.DataFrame(logs)
    if df.empty:
        return pd.DataFrame()
    df['datetime'] = pd.to_datetime(df['datetime'])
    merged = df.merge(patients[['phone', 'name']], on='phone', how='left')

    report = merged.groupby(['phone', 'name']).agg({
        'type': lambda x: {
            'compliance': (x == 'compliance').sum(),
            'noncompliance': (x == 'noncompliance').sum(),
            'side effect': (x == 'side effect').sum()
        },
        'datetime': 'max'
    }).reset_index()

    report = pd.concat([report.drop('type', axis=1), report['type'].apply(pd.Series)], axis=1)

    report.rename(columns ={'datetime':'Last Activity', 'compliance':'Compliant Days', 'noncompliance': 'Missed Days', 'side effect': 'Side Effects Reported'}, inplace = True)
    return report


@app.route("/download_report")
def downloadReport():
    df = generateReport()
    if df.empty:
        flash("No data")
        return redirect(url_for("dashboard"))
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="Compliance_Report.csv", mimetype="text/csv")


if __name__ == "__main__":
    app.run(port=5001, debug=True)





