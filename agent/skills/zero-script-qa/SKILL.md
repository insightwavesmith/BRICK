---
name: zero-script-qa
description: Use when QA should inspect declared evidence before asking for extra scripts or broad tool execution.
---

# Zero Script QA

Start with existing evidence:

```text
changed files
declared verification refs
step outputs
raw refs
claim_trace refs
Building map refs
```

Request extra commands only when the Brick work contract needs them. Do not
run mutation, approve success, or choose a route target.
