# Observability Skill

You have access to VictoriaLogs and VictoriaTraces for querying system observability data.

## Available Tools

### Log Tools (VictoriaLogs)
- **logs_search** — Search logs using LogsQL query. Returns matching log entries.
  - Use when user asks about specific errors, events, or time periods
  - Example query: `level:error AND service:backend`
  - Example query: `service:nanobot AND request_started`

- **logs_error_count** — Count errors over a time window. Returns total and breakdown by service.
  - Use when user asks "any errors?", "how many errors?", "error count"
  - Default: last 1 hour, all services

### Trace Tools (VictoriaTraces)
- **traces_list** — List recent traces for a service.
  - Use when user asks about request flow, latency, or service interactions
  - Returns trace summaries with IDs, span counts, durations

- **traces_get** — Fetch a specific trace by ID.
  - Use when you have a trace ID from logs and need full details
  - Returns span hierarchy showing request flow

## When to Use

### User asks about errors
1. First call `logs_error_count` to get overview
2. If errors found, call `logs_search` with `level:error` to see details
3. If logs mention a trace ID, call `traces_get` to investigate

### User asks about system health
1. Call `logs_error_count` with `hours=1`
2. Report: "X errors in the last hour" + breakdown by service
3. If errors exist, summarize what went wrong

### User asks about a specific service
1. Call `logs_search` with `service:<name>`
2. Call `traces_list` with `service:<name>` to see recent requests

## Response Format

- **Concise summaries**: Don't dump raw JSON
- **Highlight errors**: Bold error messages and affected services
- **Include timestamps**: When relevant
- **Trace IDs**: Mention if found, offer to investigate

## Examples

**User**: "Any errors in the last hour?"
**You**: Call `logs_error_count` with `hours=1`.
Response: "Found 5 errors in the last hour:
- backend: 3 errors (db_query failures)
- nanobot: 2 errors (connection timeouts)"

**User**: "Show me backend errors"
**You**: Call `logs_search` with `query="level:error AND service:backend"`.
Summarize the error messages found.

**User**: "Why is the system slow?"
**You**: Call `traces_list` with `service=backend` to see recent request latencies.
Look for spans with high duration.
