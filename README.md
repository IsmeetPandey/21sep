# MCP ChangeGuard

Deterministic pull-request checks for changes to an MCP server's agent-facing tool contract.

MCP tooling is increasingly good at inspecting a server's current surface. The harder CI problem is **change control**: a harmless code change can silently rename a tool, weaken an input schema, remove a required field, or change descriptions that agents rely on for tool selection.

MCP ChangeGuard compares two saved `tools/list`-style manifests and classifies the contract delta as `compatible`, `review`, or `breaking`. It is local-first, dependency-free, deterministic, and designed to run before merge.

## Why this exists

Existing MCP tooling covers runtime inspection, security auditing, conformance, and health checks. ChangeGuard focuses on a narrower workflow: **make agent-facing MCP contract changes reviewable in Git**. It does not execute an MCP server and it does not call an LLM.

## Quick start

```bash
python -m mcp_changeguard before.json after.json
```

Machine-readable output:

```bash
python -m mcp_changeguard before.json after.json --json
```

Fail CI on breaking changes:

```bash
python -m mcp_changeguard before.json after.json --fail-on breaking
```

Exit codes:

- `0` — change is below the selected failure threshold
- `1` — at least one change meets the threshold
- `2` — invalid input or usage error

## What it detects

- added and removed tools
- tool renames (when an explicit `x-changeguard-id` is present)
- description changes
- input schema changes
- required-property additions/removals
- property type changes
- enum narrowing/widening
- `additionalProperties` changes
- malformed manifests

The comparison is intentionally conservative. A change that can alter what an agent is allowed or expected to send is surfaced for review rather than guessed to be safe.

## Manifest format

ChangeGuard accepts either a bare array or the `tools/list` response shape:

```json
{
  "tools": [
    {
      "name": "search_docs",
      "description": "Search internal documentation.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"}
        },
        "required": ["query"],
        "additionalProperties": false
      }
    }
  ]
}
```

For stable rename tracking, add an optional `x-changeguard-id` to a tool. Without it, a rename is represented as a removal plus an addition because identity cannot be proven safely.

## CI

```yaml
- name: Check MCP contract
  run: python -m mcp_changeguard contracts/base.json contracts/head.json --fail-on breaking --json
```

No network access, server execution, credentials, or model calls are required.

## Security boundary

ChangeGuard treats input manifests as untrusted data. It parses JSON only, never executes values, never follows URLs, never loads configuration from the manifest, and never makes network requests.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall mcp_changeguard
```

## Scope

ChangeGuard is a contract-diff tool, not a replacement for runtime inspection, security scanning, MCP conformance testing, or semantic LLM evaluation.

## License

MIT
