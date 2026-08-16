# Runtime monitor

Status: minimal live probe available. Not a deployment twin grant.

## Split of concerns

| Layer | HOME | Role |
| --- | --- | --- |
| Local conformance | `wellmanifest/saas-lifecycle` | Fixture + digest checks (`standard/conformance.py`) |
| Onboarding profile vocabulary | this pack | Closed ids and fail-closed codes |
| Deployment twin / live probes | `subactor/www-sub-actor` | `scripts/runtime_probe.py` against pinned ADOPT revision |

## First vertical: `membership-before-payment`

Run locally (portal on `:8781`, optional Control on `:8091`):

```bash
# HOME probe (Subactor portal)
python3 /home/tom/github/subactor/www-sub-actor/scripts/runtime_probe.py \
  --www http://127.0.0.1:8781 --control http://127.0.0.1:8091

# Pack wrapper (ADOPT path discovery)
python3 scripts/runtime_probe.py --www http://127.0.0.1:8781 --control http://127.0.0.1:8091
```

Checks (fail closed):

1. `GET /healthz` healthy without implying membership.
2. Unauthenticated `/api/session` denied (`SAAS-ONBOARD-001`).
3. Unknown-email OTP request denied; no session (`SAAS-ONBOARD-001`).
4. Client-declared paid / forged login without membership does not activate
   (`SAAS-ONBOARD-002`).
5. Public offer (`/`) and `/legal` reachable; payment not publicly enabled by
   default.

Evidence belongs in Subactor TestQL / probe JSON (`--json`). This pack keeps
the normative codes and profile ids.
