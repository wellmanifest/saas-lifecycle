# Ticket 012: Restore pinned SaaS DSL manifest conformance

- **ID**: ticket-012
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-11

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requests continuation through Willman, backlog Issues and PR repairs, with earlier protected publication instruction. Parent SAAS-002 / wellmanifest PLF-002. Restore compatibility with the declared immutable b7d0595 DSL schema; observed baseline rejects decisionProtocol. Preserve domain semantics, managed pins and terminal Issue15/PR21. Canonical result: [harmonization report](https://github.com/subactor/docs/blob/2d8956bd37a937e3a3e95c112ea5dc45115ef7cd/architecture/analysis/wellmanifest-standards-harmonization.md).

## Acceptance criteria

- [x] AC-01: Exact declared checker changes from DSL-FAIL to DSL-PASS.
- [x] AC-02: Domain conformance and scoped managed governance pass.
- [ ] AC-03: Independent protected publication is requested for the frozen tested head.
