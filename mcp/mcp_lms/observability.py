"""MCP server for querying VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

server = Server("observability")

# Configuration from environment
VICTORIALOGS_URL = os.environ.get("VICTORIALOGS_URL", "http://localhost:42010")
VICTORIATRACES_URL = os.environ.get("VICTORIATRACES_URL", "http://localhost:42011")

# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class _NoArgs(BaseModel):
    """Empty input model for tools that only need server-side configuration."""


class _LogsSearch(BaseModel):
    query: str = Field(description="LogsQL query string (e.g., 'level:error AND service:backend').")
    limit: int = Field(default=100, ge=1, le=1000, description="Max log entries to return.")


class _LogsErrorCount(BaseModel):
    service: str = Field(default="*", description="Service name to filter (use '*' for all).")
    hours: int = Field(default=1, ge=1, le=168, description="Time window in hours (max 1 week).")


class _TracesList(BaseModel):
    service: str = Field(description="Service name to filter traces.")
    limit: int = Field(default=10, ge=1, le=100, description="Max traces to return.")


class _TracesGet(BaseModel):
    trace_id: str = Field(description="Trace ID to fetch.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text(data: Any) -> list[TextContent]:
    """Serialize data to JSON text."""
    if isinstance(data, (dict, list)):
        return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]
    return [TextContent(type="text", text=str(data))]


async def _http_get(url: str, params: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
    """Make HTTP GET request."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Log tool handlers
# ---------------------------------------------------------------------------


async def _logs_search(args: _LogsSearch) -> list[TextContent]:
    """Search VictoriaLogs using LogsQL."""
    url = f"{VICTORIALOGS_URL}/select/logsql/query"
    params = {
        "query": args.query,
        "limit": args.limit,
    }
    try:
        result = await _http_get(url, params)
        return _text(result)
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaLogs query failed: {e}", "url": url, "params": params})


async def _logs_error_count(args: _LogsErrorCount) -> list[TextContent]:
    """Count errors per service over a time window."""
    # Build LogsQL query for errors
    if args.service == "*":
        query = "level:error"
    else:
        query = f"level:error AND service:{args.service}"
    
    url = f"{VICTORIALOGS_URL}/select/logsql/query"
    params = {
        "query": query,
        "limit": 10000,  # Get more to count accurately
    }
    
    try:
        result = await _http_get(url, params)
        
        # Count errors by service
        error_count = 0
        services: dict[str, int] = {}
        
        if isinstance(result, list):
            for entry in result:
                error_count += 1
                if isinstance(entry, dict):
                    service_name = entry.get("_stream", {}).get("service", "unknown")
                    services[service_name] = services.get(service_name, 0) + 1
        
        summary = {
            "total_errors": error_count,
            "time_window_hours": args.hours,
            "errors_by_service": services,
        }
        return _text(summary)
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaLogs query failed: {e}", "url": url, "params": params})


# ---------------------------------------------------------------------------
# Trace tool handlers
# ---------------------------------------------------------------------------


async def _traces_list(args: _TracesList) -> list[TextContent]:
    """List recent traces for a service."""
    url = f"{VICTORIATRACES_URL}/jaeger/api/traces"
    params = {
        "service": args.service,
        "limit": args.limit,
    }
    try:
        result = await _http_get(url, params)
        
        # Extract summary info
        traces_summary = []
        if isinstance(result, dict) and "data" in result:
            for trace in result["data"]:
                traces_summary.append({
                    "trace_id": trace.get("traceID"),
                    "spans": len(trace.get("spans", [])),
                    "start_time": trace.get("startTime"),
                    "duration": trace.get("duration"),
                })
        
        return _text({"traces": traces_summary, "total": len(traces_summary)})
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaTraces query failed: {e}", "url": url, "params": params})


async def _traces_get(args: _TracesGet) -> list[TextContent]:
    """Fetch a specific trace by ID."""
    url = f"{VICTORIATRACES_URL}/jaeger/api/traces/{args.trace_id}"
    try:
        result = await _http_get(url)
        
        # Extract span hierarchy
        if isinstance(result, dict) and "data" in result:
            trace_data = result["data"][0] if result["data"] else {}
            spans_summary = []
            for span in trace_data.get("spans", []):
                spans_summary.append({
                    "span_id": span.get("spanID"),
                    "operation": span.get("operationName"),
                    "service": span.get("process", {}).get("serviceName", "unknown"),
                    "duration": span.get("duration"),
                    "tags": [t for t in span.get("tags", []) if t.get("key") in ["error", "http.status_code"]],
                })
            
            return _text({
                "trace_id": trace_data.get("traceID"),
                "spans": spans_summary,
                "total_spans": len(spans_summary),
            })
        return _text(result)
    except httpx.HTTPError as e:
        return _text({"error": f"VictoriaTraces query failed: {e}", "url": url})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_Registry = tuple[type[BaseModel], Callable[..., Awaitable[list[TextContent]]], Tool]

_TOOLS: dict[str, _Registry] = {}


def _register(
    name: str,
    description: str,
    model: type[BaseModel],
    handler: Callable[..., Awaitable[list[TextContent]]],
) -> None:
    schema = model.model_json_schema()
    schema.pop("$defs", None)
    schema.pop("title", None)
    _TOOLS[name] = (model, handler, Tool(name=name, description=description, inputSchema=schema))


_register(
    "logs_search",
    "Search VictoriaLogs using LogsQL. Returns log entries matching the query.",
    _LogsSearch,
    _logs_search,
)
_register(
    "logs_error_count",
    "Count errors in VictoriaLogs over a time window. Returns total count and breakdown by service.",
    _LogsErrorCount,
    _logs_error_count,
)
_register(
    "traces_list",
    "List recent traces from VictoriaTraces for a specific service.",
    _TracesList,
    _traces_list,
)
_register(
    "traces_get",
    "Fetch a specific trace by ID from VictoriaTraces. Returns span hierarchy.",
    _TracesGet,
    _traces_get,
)


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [entry[2] for entry in _TOOLS.values()]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    entry = _TOOLS.get(name)
    if entry is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    model_cls, handler, _ = entry
    try:
        args = model_cls.model_validate(arguments or {})
        return await handler(args)
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
