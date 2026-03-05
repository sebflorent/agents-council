import os

# Google OAuth — obtain via: python3 briefings/get_token.py
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
WORK_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

WORK_EMAIL = os.environ.get("WORK_EMAIL", "you@yourcompany.com")

# Jira — API token from https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://your-org.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", WORK_EMAIL)
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

BRIEFING_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Paris")
