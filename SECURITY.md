# Security

Career Forge handles sensitive job-search data, including email metadata,
recruiter contacts, company records, applications, and generated materials.

## Supported Versions

Only the latest `main` branch is supported before the first public release.

## Reporting a Vulnerability

Do not open public issues containing secrets, email content, tokens, or private
job-search data. Use a private disclosure channel once the project is hosted.

## Secrets

Never commit:

- `.env`
- Gmail OAuth credentials or tokens
- Notion integration tokens
- Logfire write tokens
- OpenAI/model-provider API keys
- real resumes, cover letters, emails, or recruiter messages

## Local Data

Runtime files are written under `.career_forge/` by default and are ignored by Git.
