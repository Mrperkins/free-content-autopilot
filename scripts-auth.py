"""Run locally once, then put the refresh token in GitHub Actions secrets."""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
if len(sys.argv)!=2:
    raise SystemExit('Usage: python scripts-auth.py /path/to/client_secret.json')
flow=InstalledAppFlow.from_client_secrets_file(
    sys.argv[1],scopes=['https://www.googleapis.com/auth/youtube.upload'])
credentials=flow.run_local_server(port=0,access_type='offline',prompt='consent')
if not credentials.refresh_token:
    raise SystemExit('No offline refresh token granted; inspect OAuth consent setup')
print('\nSAVE ONLY AS GITHUB SECRET YT_REFRESH_TOKEN:\n'+credentials.refresh_token+'\n')
