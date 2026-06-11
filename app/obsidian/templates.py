AGENT_RUN_TEMPLATE = """---
type: agent_run
run_id: {run_id}
agent_id: {agent_id}
domain: {domain}
status: {status}
tags:
  - neuroagent
  - agent-run
  - {domain}
---

# Agent Run: {agent_id}

## User Request

{user_request}

## Execution Plan

{execution_plan}

## Key Findings

{findings}
"""
