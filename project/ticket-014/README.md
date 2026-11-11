# Ticket 014: Modularize and harden SaaS lifecycle conformance

- **ID**: ticket-014
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

Decompose `standard/conformance.py` (723 lines) into six focused modules strictly `< 500` lines (`saas_contracts.py`, `saas_validators.py`, `saas_usage.py`, `saas_examples.py`, `saas_profiles.py`, `conformance.py`), enforce strict `type(v) is int`, JSON Schema field/length/enum parity, unhashable list rejection, duplicate JSON key and symlink rejection, inline bearer/private-key secret detection, and narrowed `except ContractError:` adversarial verification, and sync `dsl-manifest.json`.

## Acceptance criteria

- [x] AC-01: All owned `standard/*.py` modules stay `< 500` lines, and `python3 standard/conformance.py --all`, `./project/governance-check.sh --base origin/main`, and `wellman check` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
