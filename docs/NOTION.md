# Notion

Notion is the source of truth.

## Required Databases

- Opportunities Pipeline
- Companies
- Contacts / Recruiters
- Applications
- Interviews
- Follow-Ups
- Career Materials
- Outreach Templates
- Research Notes
- Tasks
- Weekly Reviews

## Live Write Requirements

Every target database used by live upsert should include a `Dedupe Key`
rich-text property. The Notion gateway uses this property to find existing pages
before creating new ones.

## Integration Setup

Create the integration in Notion's developer UI:

1. Open `https://www.notion.so/profile/integrations`.
2. Create an internal integration named `Career Forge`.
3. Copy the internal integration secret.
4. Share the Career Command Center page/databases with the integration.
5. Add the token to ignored local `.env`:

```bash
CAREER_FORGE_NOTION_TOKEN=secret_xxx
```

The Notion connector used by Codex can read/write workspace pages, but it cannot
create a Notion API integration secret for the local application. That secret
must come from Notion's developer UI.

## Safety

- Dry-run mode is the default for CLI sync commands.
- Mutations are planned before execution.
- Executed mutations are recorded in the event log.
- Duplicate dedupe keys are skipped.
- Failures produce retry/error events.
