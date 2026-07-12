#!/usr/bin/env bash
set -euo pipefail

mkdir -p .career_forge
touch .env

upsert_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    printf '%s\0%s' "$key" "$value" | python -c '
from pathlib import Path
import sys

raw = sys.stdin.buffer.read()
key, value = (part.decode() for part in raw.split(b"\0", 1))
path = Path(".env")
lines = path.read_text(encoding="utf-8").splitlines()
path.write_text(
    "\n".join(f"{key}={value}" if line.startswith(f"{key}=") else line for line in lines) + "\n",
    encoding="utf-8",
)
'
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

prompt_secret() {
  local label="$1"
  local value
  read -rsp "$label: " value
  printf '\n' >&2
  printf '%s' "$value"
}

prompt_value() {
  local label="$1"
  local value
  read -r -p "$label: " value
  printf '%s' "$value"
}

echo "This writes secrets only to ignored local files: .env and .career_forge/gmail_credentials.json"

google_client_id="$(prompt_secret 'Google OAuth Client ID')"
google_client_secret="$(prompt_secret 'Google OAuth Client Secret')"
openai_api_key="$(prompt_secret 'OpenAI API key')"
notion_token="$(prompt_secret 'Notion integration token (press Enter to skip)')"
opportunities_database_id="$(prompt_value 'Notion Opportunities database ID (press Enter to skip)')"
companies_database_id="$(prompt_value 'Notion Companies database ID (press Enter to skip)')"
contacts_database_id="$(prompt_value 'Notion Contacts database ID (press Enter to skip)')"
applications_database_id="$(prompt_value 'Notion Applications database ID (press Enter to skip)')"

printf '%s\0%s' "$google_client_id" "$google_client_secret" | python -c '
from pathlib import Path
import json
import sys

raw = sys.stdin.buffer.read()
client_id, client_secret = (part.decode() for part in raw.split(b"\0", 1))
payload = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}
path = Path(".career_forge/gmail_credentials.json")
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
'

upsert_env "CAREER_FORGE_GMAIL_CREDENTIALS_PATH" ".career_forge/gmail_credentials.json"
upsert_env "CAREER_FORGE_GMAIL_TOKEN_PATH" ".career_forge/gmail_token.json"
upsert_env "CAREER_FORGE_AI_PROVIDER" "pydantic-ai"
upsert_env "CAREER_FORGE_PYDANTIC_AI_MODEL" "openai:gpt-5.2"
upsert_env "OPENAI_API_KEY" "$openai_api_key"

if [[ -n "$notion_token" ]]; then
  upsert_env "CAREER_FORGE_NOTION_TOKEN" "$notion_token"
fi
if [[ -n "$opportunities_database_id" ]]; then
  upsert_env "CAREER_FORGE_OPPORTUNITIES_DATABASE_ID" "$opportunities_database_id"
fi
if [[ -n "$companies_database_id" ]]; then
  upsert_env "CAREER_FORGE_COMPANIES_DATABASE_ID" "$companies_database_id"
fi
if [[ -n "$contacts_database_id" ]]; then
  upsert_env "CAREER_FORGE_CONTACTS_DATABASE_ID" "$contacts_database_id"
fi
if [[ -n "$applications_database_id" ]]; then
  upsert_env "CAREER_FORGE_APPLICATIONS_DATABASE_ID" "$applications_database_id"
fi

echo "Local secrets written. Run: uv run career-forge check-setup"
