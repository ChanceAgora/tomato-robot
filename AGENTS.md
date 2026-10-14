# Agent coding protocol
Guidelines marked `*` are CRITICAL; operate within all of them at all times. If one conflicts with an explicit user instruction, surface the conflict rather than silently choosing.

## Decision making
- *Human-in-the-loop: ask before non-obvious design decisions, tradeoffs to consider or difficult-to-reverse choices, and/or whenever the task is ambiguous or underspecified. Proceed autonomously on unambiguous implementation work.
- When proceeding autonomously on a mildly ambiguous point, state the assumption you made so it can be reviewed.
- Adding, removing, or upgrading a dependency is a non-obvious decision—surface it with a brief rationale rather than pulling one in silently.

## Orienting in a repo
- Before substantive work in an unfamiliar codebase, read the README and any AGENTS.md/CLAUDE.md, and identify the build, test, and lint commands.
- Read existing code you'll touch; match its naming, structure, and patterns.

## Before changing code
- Change only what the task requires—no unrelated refactors or doc churn.
- Extend existing code rather than duplicating similar logic.

## Architecture & quality
- *Separation of concerns, modular boundaries, single responsibility, idiomatic patterns for the stack.
- Keep config, docs, and source in conventional places for the ecosystem.
- Document functions whose intent isn't clear from the signature; comment non-trivial logic, business rules, workarounds, and algorithmic choices ("why" over "what").
- Fix root causes; no broad catches or silent failures.

## Security
- *NEVER read, print, log, or commit secrets, credentials, or tokens; only ever ask for env vars or use the project's secret mechanism.
- Validate and sanitize external input; treat data from files, network, and user input as untrusted.
- *Enforce high security standards and minimize vulnerabilities in software.

## Workflow
- *Enforce correctness structurally: automate validation (tests, linters, schema assertions) and prefer automation over manual steps so work is repeatable and auditable.
- Implement in small, verifiable steps; run relevant lint/tests/build before completing a task.
- With shell access, run checks yourself and report actual output. Never mark work done on a failing or unrun check.
- One logical commit per task. Conventional Commits: `type(optional scope): description`, imperative mood, subject <= ~50 chars. No AI co-author trailers.
- Don't push or open PRs autonomously unless asked; leave commits local for review.

## Testing & completion
- *Add or update tests for behavior you create or change, using stack-appropriate libraries. Match the existing test style/framework; ask before introducing a new one.
- *Keep docs UP TO DATE: update or create them whenever setup, workflows, APIs, architecture, or behaviors change.
