# gen_token.py — Run once to generate credentials/token.json, then delete this file
# Usage: python gen_token.py

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials/google_credentials.json", SCOPES
)
creds = flow.run_local_server(port=0)

with open("credentials/token.json", "w") as f:
    f.write(creds.to_json())

print("\n=== Success! ===")
print("credentials/token.json created.")
print(f"\nYour YOUTUBE_REFRESH_TOKEN:\n{creds.refresh_token}")
print("\nCopy this token and add it to your .env file.")
