from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import logging
from pytz import timezone

# -----------------------------------------------------
# Flask App + Scheduler Setup
# -----------------------------------------------------
app = Flask(__name__)

scheduler = BackgroundScheduler(timezone=timezone("Asia/Kolkata"))

session = requests.Session()
logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

LOGIN_URL = "https://hrms.vc-erp.com:6443/HRMS/validEmployee"
PUNCH_URL = "https://hrms.vc-erp.com:6443/HRMS/setEmployeeIn_outPunch"

USERNAME = "VE1372@vcerp.com"
PASSWORD = "!!Ram@2025"


# -----------------------------------------------------
# Login Function (Reusable)
# -----------------------------------------------------
def login():
    """
    Re-login to HRMS and refresh session cookies.
    """
    try:
        login_data = {"username": USERNAME, "password": PASSWORD}
        response = session.post(LOGIN_URL, data=login_data, timeout=100)

        soup = BeautifulSoup(response.text, "html.parser")

        if "HRMS | Dashboard" in soup.get_text():
            logging.info("Session login successful!")
            return {"success": True, "data": soup.get_text()}
        else:
            logging.error("Login failed (credentials rejected or login page returned).")
            return {"success": False, "error": "Login failed (credentials rejected or login page returned)."}

    except Exception as e:
        logging.error(f"Login error: {e}")
        return {"success": False,"error": str(e)}
    
# -----------------------------------------------------
# Punch IN/OUT Function
# -----------------------------------------------------
def punch_in_out(id=1993):
    """
    Call the punch API after login is already done.
    """
    try:
        params = {"employee_id": id}
        response = session.post(PUNCH_URL, params=params, timeout=100)

        soup = BeautifulSoup(response.text, "html.parser")
        msg = soup.get_text(strip=True)

        logging.info(f"Punch response: {msg}")

        if "Attendance Punched." in msg:
            logging.info(f"Punch In Time :{datetime.now()}")
            logging.info("Punch In completed!")
        else:
            logging.warning("Punch action failed!")

    except Exception as e:
        logging.error(f"Punch error: {e}")


# -----------------------------------------------------
# Scheduled Job: Login first THEN punch
# -----------------------------------------------------
def job_login_then_punch():
    """
    This function runs after 9 hours:
    1. Logs in again (session refresh)
    2. Calls Punch In/Out
    """
    logging.info("Scheduled job triggered. Re-authenticating session...")

    response = login()
    if response.get("success", False):   # <--- LOGIN FIRST
        punch_in_out()  # <--- THEN PUNCH
    else:
        logging.error("Scheduled punch canceled due to login failure.")

# -----------------------------------------------------
# Schedule Job Function
# -----------------------------------------------------
def schedule_job_after_9_hours():
    try:
        # run_time = datetime.now() + timedelta(hours=9, minutes=5)
        run_time = datetime.now() + timedelta(minutes=2)

        scheduler.add_job(
            job_login_then_punch,  # <--- updated here
            trigger="date",
            run_date=run_time,
            id="punch_job",
            replace_existing=True
        )

        # # if not scheduler.running:
        # scheduler.start()

        logging.info(f"Job scheduled at {run_time}")

    except Exception as e:
        logging.error(f"Scheduling error: {e}")


# -----------------------------------------------------
# Route: Perform Login + Auto Punch Logic
# -----------------------------------------------------
@app.route("/auto_punch", methods=["GET"])
def auto_punch():
    try:
        login_result = login()
        if not login_result.get("success", False):  # First login
            return jsonify({"login": False, "error": login_result.get("error", "Login failed")}), 401

        # After login, check punch-in status
        
        is_punched_in = "Punch Out" in login_result.get("data", "")
        
        print(login_result)
        
        schedule_job_after_9_hours()
        if not is_punched_in:
            job = scheduler.get_job("punch_job")
            if job:
                return jsonify({
                    "login": True,
                    "punch_in": False,
                    "job_scheduled": {
                    "job_id": job.id,
                    "next_run_time": str(job.next_run_time),
                    "status": "Scheduled"
                }
                })
            else:
                return jsonify({
                    "login": True,
                    "punch_in": False,
                    "job_scheduled":"Job Not Found." 
                })


        return jsonify({
            "login": True,
            "punch_in": True,
            "job_scheduled": False,
            "message": "Already punched in"
        })

    except Exception as e:
        logging.error(f"Auto punch error: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------
# Route: Check Scheduled Job
# -----------------------------------------------------
@app.route("/job_status", methods=["GET"])
def job_status():
    job = scheduler.get_job("punch_job")
    if job:
        return jsonify({
            "job_id": job.id,
            "next_run_time": str(job.next_run_time),
            "status": "Scheduled"
        })
    return jsonify({"status": "No job scheduled"})


# -----------------------------------------------------
# Route: for keep server alive
# -----------------------------------------------------
@app.route("/")
def ping():
    return f"Tiger abhi zinda hai.{datetime.now()}"


# -----------------------------------------------------
# Flask Run
# -----------------------------------------------------
if __name__ == "__main__":
    # THE MOST IMPORTANT FIX
    scheduler.start()

    # Disable reloader (prevents double execution)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
