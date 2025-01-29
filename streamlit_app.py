import streamlit as st
import google.generativeai as genai
from jira import JIRA
import smtplib
import json
import re
from email.mime.text import MIMEText

# 🔹 Configure Google API Key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 🔹 Jira Credentials (Stored Securely in Streamlit Secrets)
JIRA_SERVER = "https://evertechnologies.atlassian.net"
JIRA_EMAIL = st.secrets["JIRA_EMAIL"]
JIRA_API_TOKEN = st.secrets["JIRA_API_TOKEN"]
JIRA_PROJECT = "YOUR_PROJECT_KEY"
DEFAULT_ASSIGNEE = "responsible_person@example.com"

# 🔹 SMTP Email Configuration (For Notifications)
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USERNAME = st.secrets["SMTP_USERNAME"]
SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
EMAIL_FROM = "notifications@evertechnologies.com"
EMAIL_TO = "team@evertechnologies.com"

# 🔹 Connect to Jira API
jira_options = {"server": JIRA_SERVER}
jira = JIRA(options=jira_options, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

# 🔹 Function to Fetch Latest Open Jira Ticket
def get_latest_ticket():
    query = f'project="{JIRA_PROJECT}" AND status="Open" ORDER BY created DESC'
    issues = jira.search_issues(query, maxResults=1)
    return issues[0] if issues else None

# 🔹 AI Analysis Function (Using Google Gemini AI)
@st.cache_data(ttl=3600)
def analyze_ticket(description):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = """Analyze this email and extract:
    - Summary
    - Sentiment (Positive, Neutral, Negative)
    - Root Cause
    - Actionable Steps
    - Severity Level (High, Medium, Low)
    - Responsible Person (if identifiable)
    
    Text:\n\n"""
    response = model.generate_content(prompt + description[:1000])
    return response.text.strip()

# 🔹 Function to Detect Severity Level
def detect_severity(text):
    if "urgent" in text.lower() or "critical" in text.lower():
        return "High"
    elif "issue" in text.lower() or "problem" in text.lower():
        return "Medium"
    return "Low"

# 🔹 Function to Assign Ticket to Responsible Person
def assign_ticket(ticket_id, assignee_email):
    try:
        user = jira.search_users(assignee_email)
        if user:
            jira.assign_issue(ticket_id, user[0].accountId)
            return f"Issue assigned to {assignee_email}"
        else:
            return "No valid user found for assignment"
    except Exception as e:
        return f"Assignment Error: {e}"

# 🔹 Function to Post Comment on Jira Ticket
def comment_on_ticket(ticket_id, analysis, severity):
    comment_text = f"🔍 **Automated Analysis:**\n{analysis}\n\n🚨 **Severity Level:** {severity}"
    jira.add_comment(ticket_id, comment_text)

# 🔹 Function to Send Email Notification
def send_email_notification(ticket_id, summary, severity, assignee):
    subject = f"[Jira Alert] New Ticket Analyzed - {ticket_id} ({severity})"
    body = f"""
    A new Jira ticket has been analyzed:

    🔹 **Ticket ID:** {ticket_id}
    🔹 **Summary:** {summary}
    🔹 **Severity Level:** {severity}
    🔹 **Assigned To:** {assignee}

    Check the ticket here: {JIRA_SERVER}/browse/{ticket_id}

    - Automated Escalytics System
    """

    msg = MIMEText(body)
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        return "Email notification sent!"
    except Exception as e:
        return f"Email Error: {e}"

# 🔹 Streamlit UI
st.set_page_config(page_title="Escalytics", page_icon="📧", layout="wide")
st.title("⚡ Jira Email Analyzer & Automator")

if st.button("Analyze Latest Jira Ticket"):
    ticket = get_latest_ticket()
    
    if ticket:
        ticket_id = ticket.key
        ticket_summary = ticket.fields.summary
        ticket_description = ticket.fields.description

        st.write(f"Analyzing Ticket: **{ticket_id} - {ticket_summary}**")
        
        # 🧠 Run AI Analysis
        analysis = analyze_ticket(ticket_description)
        
        # 🏷️ Detect Severity
        severity = detect_severity(ticket_description)
        
        # 👤 Assign Ticket
        assignment_status = assign_ticket(ticket_id, DEFAULT_ASSIGNEE)

        # 📝 Post Comment on Jira
        comment_on_ticket(ticket_id, analysis, severity)

        # 📧 Send Email Notification
        email_status = send_email_notification(ticket_id, ticket_summary, severity, DEFAULT_ASSIGNEE)

        # ✅ Show Results
        st.success(f"Analysis posted as a comment on Jira ticket **{ticket_id}**!")
        st.text_area("Analysis Result:", analysis, height=200)
        st.write(f"🚨 **Severity Level:** {severity}")
        st.write(f"👤 **Assignment Status:** {assignment_status}")
        st.write(f"📩 **Email Notification:** {email_status}")

    else:
        st.warning("No new open tickets found.")
