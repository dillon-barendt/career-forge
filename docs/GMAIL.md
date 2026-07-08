# Gmail

Career Forge syncs the dedicated career inbox:

`dillon.barendt.jobs@gmail.com`

## OAuth Setup

1. Create a Google OAuth desktop client.
2. Download the client JSON.
3. Save it to `.career_forge/gmail_credentials.json`.
4. Run:

```bash
career-forge ingest-gmail --dry-run
```

The first live client run opens the OAuth browser flow and writes
`.career_forge/gmail_token.json`.

If you have a client ID and client secret but not a downloaded JSON file, run:

```bash
scripts/configure_local_secrets.sh
```

The script prompts with hidden input and writes
`.career_forge/gmail_credentials.json` locally. The file is ignored by Git.

## Single-Message Live-Write Control

Before broad live Gmail-to-Notion sync, use one known Gmail message id:

```bash
career-forge ingest-gmail-message <gmail-message-id> --dry-run
career-forge events --limit 20
career-forge ingest-gmail-message <gmail-message-id> \
  --no-dry-run \
  --mutation-index 0 \
  --confirm-message-id <gmail-message-id>
```

This path fetches one message, classifies it, prints indexed Notion mutation
candidates, and live-writes only the selected mutation. It does not acknowledge
the Gmail message or advance the broad sync checkpoint.

## Sync Behavior

- polls Gmail labels, default `INBOX`
- classifies messages with Pydantic AI
- plans Notion mutations
- records append-only events
- marks processed messages with `Career Forge/Processed`
- checkpoints the last processed message id

## Safety

Already-processed messages are skipped. Dry-run mode does not mutate Notion.
