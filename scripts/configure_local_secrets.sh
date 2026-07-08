#!/usr/bin/env bash
set -euo pipefail

mkdir -p .career_ops
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

echo "This writes secrets only to ignored local files: .env and .career_ops/gmail_credentials.json"

google_client_id="$(prompt_secret 'Google OAuth Client ID')"
google_client_secret="$(prompt_secret 'Google OAuth Client Secret')"
openai_api_key="$(prompt_secret 'OpenAI API key')"
notion_token="$(prompt_secret 'Notion integration token (press Enter to skip)')"

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
path = Path(".career_ops/gmail_credentials.json")
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
'

upsert_env "CAREER_OPS_GMAIL_CREDENTIALS_PATH" ".career_ops/gmail_credentials.json"
upsert_env "CAREER_OPS_GMAIL_TOKEN_PATH" ".career_ops/gmail_token.json"
upsert_env "CAREER_OPS_AI_PROVIDER" "pydantic-ai"
upsert_env "CAREER_OPS_PYDANTIC_AI_MODEL" "openai:gpt-5.2"
upsert_env "OPENAI_API_KEY" "$openai_api_key"

if [[ -n "$notion_token" ]]; then
  upsert_env "CAREER_OPS_NOTION_TOKEN" "$notion_token"
fi

echo "Local secrets written. Run: uv run career-ops check-setup"
