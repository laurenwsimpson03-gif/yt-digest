"""
auth_setup.py — Run ONCE locally to generate OAuth credentials.
After running, copy the output JSON into your GOOGLE_CREDENTIALS_JSON secret.
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]

print("This will open a browser window. Log in with the Google account")
print("that owns the YouTube playlist you want to add videos to.\n")

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)

output = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
}

with open("credentials.json", "w") as f:
    json.dump(output, f, indent=2)

print("\n✅ credentials.json saved.")
print("\nCopy this into your GOOGLE_CREDENTIALS_JSON GitHub secret:")
print(json.dumps(output))
