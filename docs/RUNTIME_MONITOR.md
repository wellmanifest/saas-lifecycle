# Runtime monitor (design stub)

Status: design only. Not a live deployment twin and not an execution grant.

## Split of concerns

| Layer | HOME | Role |
| --- | --- | --- |
| Local conformance | `wellmanifest/saas-lifecycle` | Fixture + digest checks (`standard/conformance.py`) |
| Onboarding profile vocabulary | this pack | Closed ids and fail-closed codes |
| Deployment twin / live probes | `subactor` platform / portal | Health, auth, payment-gate probes against a pinned ADOPT revision |

## First vertical: `membership-before-payment`

Recommended continuous checks (portal + Control, fail closed):

1. `GET /readyz` (or equivalent) returns healthy without implying membership.
2. Unauthenticated checkout / subscription create is denied (`SAAS-ONBOARD-001`).
3. Membership/OTP bind succeeds before any payment adapter call is allowed.
4. Client-declared payment success without server inspect stays non-active
   (`SAAS-ONBOARD-002`).
5. Offer pin + sales `compare-www-plans` stay green (commercial SSOT).

Evidence belongs in Subactor TestQL / deployment-twin receipts. This pack keeps
the normative codes and profile ids only.
