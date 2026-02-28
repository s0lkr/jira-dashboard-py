import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("JIRA_API_TOKEN")
jira_base_url = os.getenv("JIRA_BASE_URL")
jira_email = os.getenv("JIRA_EMAIL")

