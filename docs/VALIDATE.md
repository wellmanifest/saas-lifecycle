# VALIDATE

## Purpose

Validate the provider-neutral SaaS lifecycle contract, adapter profiles, and
adversarial commercial-lifecycle cases without contacting a provider.

## Syntax

```sh
python3 standard/conformance.py --all
```

## Inputs

- `standard/saas-lifecycle.schema.json`;
- `standard/saas-lifecycle.v1.gbnf`;
- the deterministic fixtures embedded in `standard/conformance.py`.

## Outputs

A JSON conformance receipt containing bound digests, positive variant counts,
adapter profile counts, and the rejected adversarial case names.

## Errors

- `SAAS-ONBOARD-001` — onboarding state violates the lifecycle boundary.
- `SAAS-ONBOARD-002` — onboarding evidence or transition ordering is invalid.

## Examples

```sh
python3 standard/conformance.py --all
# {"ok": true, "schema": "wellmanifest.saas-lifecycle-conformance/v1", ...}
```
