import requests
import time
from datetime import datetime
from collections import deque

project_name = 'AIIB TnD HES WEB MONITORING'
# Define Teams webhook URL
TEAMS_WEBHOOK_URL = "https://sinhaludyogpvtltd.webhook.office.com/webhookb2/7612f105-7a99-4aff-acfd-6c0a3eae7ab8@fea0e8be-f07f-4698-aca3-eaef84810c21/IncomingWebhook/7e4c6f61f41145a4ba32ec296b7c683e/e40109fd-466b-4161-b58a-408a9e049641/V2W2MsWTktw3yRUbHKfWHal5gKLhsF6VcuAxRN1EMsYZE1"

# Queue to keep track of the last few response codes and timestamps
status_history = deque(maxlen=5)
alert_interval = 300  # 5 minutes in seconds

# State to track if the webpage is down
is_down = False
last_alert_time = 0

# Hash Map for error code descriptions
error_map = {
    200: "OK - The page is online and operational.",
    301: "Moved Permanently - The resource has been moved to a new URL.",
    302: "Found (Temporary Redirect) - The page temporarily redirects to another URL.",
    400: "Bad Request - The server cannot process the request due to a client error.",
    401: "Unauthorized - Authentication required or invalid credentials.",
    403: "Forbidden - Access to the resource is denied.",
    404: "Not Found - The requested page does not exist.",
    408: "Request Timeout - The server timed out waiting for the request.",
    500: "Internal Server Error - A server error occurred.",
    502: "Bad Gateway - Received an invalid response from the upstream server.",
    503: "Service Unavailable - The server is overloaded or down for maintenance.",
    504: "Gateway Timeout - The upstream server did not respond in time.",
    "offline or unreachable": "The page is offline or unreachable.",
    "timed out": "The request to the page timed out.",
}

def send_teams_alert(url, status, last_checked, is_critical):
    """Sends an alert to Microsoft Teams."""
    status_description = error_map.get(status, "Unknown status code")
    
    if is_critical:
        message = (
            f"**🔹 {project_name} 🔹**\n\n"
            f"🚨 **Critical Alert: HES Webpage Unavailable!** 🚨\n\n"
            f"- **URL:** [Visit Page]({url})\n"
            f"- **Status:** 🔴 {status_description} **(Status Code: {status}) 🔴**\n"
            f"- **Last Checked:** {last_checked}\n\n"
            f"⚠️ **Immediate attention required to restore functionality.**"
        )
    else:
        message = (
            f"**🔹 {project_name} 🔹**\n\n"
            f"✅ **Status Update: HES Webpage Restored** ✅\n\n"
            f"- **URL:** [Visit Page]({url})\n"
            f"- **Status:** 🟢 ONLINE **(Status Code: {status}) 🟢**\n"
            f"- **Last Checked:** {last_checked}\n\n"
            f"ℹ️ **The webpage is now operational and accessible.**"
        )

    payload = {"text": message}
    response = requests.post(TEAMS_WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        print(f"Alert sent to Teams: {message}")
    else:
        print(f"Failed to send alert: {response.text}")

def check_page_status(url):
    global is_down, last_alert_time
    try:
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add the status to the history queue
        status_history.append((status_code, last_checked))
        
        if status_code == 200:
            if is_down:  # Send recovery alert immediately
                send_teams_alert(url, status_code, last_checked, is_critical=False)
                is_down = False  # Reset down state
            print(f"The page {url} is online.")
        else:
            if not is_down or (time.time() - last_alert_time) >= alert_interval:
                send_teams_alert(url, status_code, last_checked, is_critical=True)
                is_down = True
                last_alert_time = time.time()
            print(f"The page {url} returned status code: {status_code}")
    
    except requests.ConnectionError:
        if not is_down:
            send_teams_alert(url, "offline or unreachable", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), is_critical=True)
            is_down = True
            last_alert_time = time.time()
        print(f"The page {url} is offline or unreachable.")
    except requests.Timeout:
        if not is_down:
            send_teams_alert(url, "timed out", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), is_critical=True)
            is_down = True
            last_alert_time = time.time()
        print(f"The request to {url} timed out.")
    except Exception as e:
        if not is_down:
            send_teams_alert(url, f"error: {str(e)}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), is_critical=True)
            is_down = True
            last_alert_time = time.time()
        print(f"An error occurred while accessing {url}: {e}")

# Main service loop
url_to_check = "https://pue-hes-tnd.apdcl.co"
try:
    while True:
        check_page_status(url_to_check)
        time.sleep(60 if not is_down else 60)  # Check every minute even when down
except KeyboardInterrupt:
    print("Monitoring stopped.")
