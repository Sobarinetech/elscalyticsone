import streamlit as st
import google.generativeai as genai
import requests
import json
import re
from requests.auth import HTTPBasicAuth

# Configure API Key securely from Streamlit's secrets
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Jira Configuration
JIRA_BASE_URL = "https://evertechnologies.atlassian.net/rest/api/3/"
JIRA_EMAIL = st.secrets["JIRA_EMAIL"]
JIRA_API_TOKEN = st.secrets["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY = "YOUR_PROJECT_KEY"

# Streamlit UI
st.set_page_config(page_title="Jira Ticket Analyzer", page_icon="📌", layout="wide")
st.title("Jira Ticket Analyzer")
st.write("Analyze Jira tickets and automatically post insights.")

# Fetch the latest Jira ticket
def get_latest_jira_ticket():
    url = f"{JIRA_BASE_URL}search?jql=project={JIRA_PROJECT_KEY}&orderBy=created DESC&maxResults=1"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN))
    
    if response.status_code == 200:
        issues = response.json().get("issues", [])
        if issues:
            return issues[0]
    
    st.error("Failed to fetch Jira ticket.")
    return None

# AI Analysis Function
def analyze_ticket(summary, description):
    prompt = (f"Analyze the following Jira ticket and provide insights:\n"
              f"Summary: {summary}\n"
              f"Description: {description}\n"
              f"Provide sentiment, key highlights, severity, risk assessment, root cause, and suggested actions.")
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"AI Analysis Error: {e}")
        return ""

# Post Comment to Jira Ticket
def post_comment_to_jira(ticket_id, comment):
    url = f"{JIRA_BASE_URL}issue/{ticket_id}/comment"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    data = json.dumps({"body": comment})
    response = requests.post(url, headers=headers, auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN), data=data)
    
    if response.status_code == 201:
        st.success("Analysis posted as a comment on Jira ticket.")
    else:
        st.error("Failed to post comment on Jira ticket.")

# Main Execution
latest_ticket = get_latest_jira_ticket()
if latest_ticket:
    ticket_id = latest_ticket["key"]
    summary = latest_ticket["fields"].get("summary", "No summary available")
    description = latest_ticket["fields"].get("description", {}).get("content", "No description available")
    
    st.subheader(f"Latest Ticket: {ticket_id}")
    st.write(f"**Summary:** {summary}")
    st.write(f"**Description:** {description}")
    
    if st.button("Analyze Ticket"):
        analysis = analyze_ticket(summary, description)
        st.subheader("Analysis Result")
        st.write(analysis)
        post_comment_to_jira(ticket_id, analysis)
