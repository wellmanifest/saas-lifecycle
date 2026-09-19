# Ticket 009: Pin planfile sync reusable workflow to immutable SHA

- **ID**: ticket-009
- **Owner**: unresolved:human
- **Status**: DONE
- **Created**: 2026-09-16

## Goal and scope

Replace the mutable \`v0.1.126\` tag reference in
\`.github/workflows/planfile-github-sync.yml\` with the immutable commit SHA
\`e79d79509c050514ba434c3bd6589f932b91c920\` that the tag points at.

## Problem

The workflow holds \`issues: write\` on an hourly schedule while referencing a
third-party reusable workflow by a movable tag. The independent Validator's
semantic review flagged this during the fleet rollout.

## Acceptance criteria

- [x] AC-01: \`uses:\` references the immutable SHA with a trailing version
  comment.
- [x] AC-02: No other behavior changes.

## Session authorization

Continuation of the 2026-09-16 automation-completion session authorized by
the repository owner.
