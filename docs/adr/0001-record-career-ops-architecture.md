# ADR 0001: Preserve Notion-Centered Career Forge Architecture

Date: 2026-07-08

## Status

Accepted

## Context

Career Forge automates a personal software engineering job search. The system
needs reliable tracking, low manual burden, and safe automation around private
career data.

## Decision

Use Notion as the source of truth. Keep business logic independent from
providers. Use Pydantic AI for structured intelligence and Logfire for
observability. All live external writes must be idempotent and traceable.

## Consequences

- Provider implementations can evolve without changing domain workflows.
- Local tests can use fake providers.
- Notion schema changes must be handled carefully.
- Event logs and dry-runs are mandatory for production safety.
