# Ticket 007: Assign the DSL manifest to the integration workstream

- **ID**: ticket-007
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Repair target governance so `dsl-manifest.json` has one explicit owner. The
file binds hashes of the standard schema and conformance artifacts and must be
updated atomically by the integration workstream whenever those artifacts
change. Today it is listed by the DSL pack but omitted from every governance
workstream, making correct standard publication impossible.

The user's request to adapt contradictory Wellmanifest rules and publish the
result is recorded as `SESSION_EXECUTION_AUTHORIZATION`. Protected exact-head
review remains the only merge authority.

## Acceptance criteria

- [x] AC-01: `dsl-manifest.json` is owned by exactly the integration workstream.
- [x] AC-02: Governance accepts future atomic schema-plus-manifest changes.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
