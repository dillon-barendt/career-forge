# Gmail

Career Ops syncs the dedicated career inbox:

`dillon.barendt.jobs@gmail.com`

## OAuth Setup

1. Create a Google OAuth desktop client.
2. Download the client JSON.
3. Save it to `.career_ops/gmail_credentials.json`.
4. Run:

```bash
career-ops ingest-gmail --dry-run
```

The first live client run opens the OAuth browser flow and writes
`.career_ops/gmail_token.json`.

If you have a client ID and client secret but not a downloaded JSON file, run:

```bash
scripts/configure_local_secrets.sh
```

The script prompts with hidden input and writes
`.career_ops/gmail_credentials.json` locally. The file is ignored by Git.

## Sync Behavior

- polls Gmail labels, default `INBOX`
- classifies messages with Pydantic AI
- plans Notion mutations
- records append-only events
- marks processed messages with `Career Ops/Processed`
- checkpoints the last processed message id

## Safety

Already-processed messages are skipped. Dry-run mode does not mutate Notion.
