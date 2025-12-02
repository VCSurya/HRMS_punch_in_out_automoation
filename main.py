from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import logging

# -----------------------------------------------------
# Flask App + Scheduler Setup
# -----------------------------------------------------
app = Flask(__name__)

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
# Route: for keep server alive
# -----------------------------------------------------
@app.route("/punch")
def ping():
    response = login()
    if response.get("success", False):   # <--- LOGIN FIRST
        punch_in_out()  # <--- THEN PUNCH
    else:
        logging.error("Scheduled punch canceled due to login failure.")

    return "Server is alive!"

# -----------------------------------------------------
# Flask Run
# -----------------------------------------------------
if __name__ == "__main__":
    # Disable reloader (prevents double execution)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
