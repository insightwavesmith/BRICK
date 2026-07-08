# Slack Alert All-Presets Task

## Objective
Prepare the Brick Protocol support-only Slack alert path for Building start, finish, and human-or-COO intervention observations.

## Required Sources
- brick_protocol/support/operator/reporter.py
- brick_protocol/support/operator/report_sinks.py
- brick_protocol/support/operator/run.py
- brick_protocol/support/operator/driver.py
- project/brick-protocol/PROGRESS.md

## Read Scope
- brick_protocol/brick/**
- brick_protocol/agent/**
- brick_protocol/link/**
- brick_protocol/support/operator/**
- brick_protocol/support/checkers/**
- project/brick-protocol/status/kernel/**

## Write Scope
- brick_protocol/support/operator/**
- brick_protocol/support/checkers/**
- project/brick-protocol/status/kernel/**

## Forbidden Surfaces
- .git/**
- .claude/**
- credential, token, auth, or session bodies
- real Slack delivery
- git commit or push
- provider runtime changes
- scheduler, queue, or retry runtime

## Constraints
- Slack is a support observation sink only, not source truth.
- Notify only Building start, Building finish, and human-or-COO intervention.
- Do not treat routine internal step completion as a Slack alert requirement.
- Do not let support choose Movement, target, success, or quality.

## Done Criteria
- A declared Building Plan can carry this task source through preset expansion.
- Evidence records task source provenance, preset expansion, declared plan, Link policy, and Building frontier.
- Any Slack delivery remains disabled unless separately admitted by human/COO disposition.

## Proof Limits
- Real Slack delivery is not proven.
- Provider behavior is not proven.
- Semantic correctness of any future implementation is not proven.
- Checker green remains support evidence only.
