# SaaS Lifecycle logic flow

## Signup, trial and conversion

```mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> MembershipVerified: identity service confirms membership
    MembershipVerified --> TrialActive: explicit start_trial under offer policy
    MembershipVerified --> PaymentPending: paid plan selected
    TrialActive --> TrialExpiring: verified notice boundary reached
    TrialActive --> Cancelled: cancelled before charge
    TrialExpiring --> PaymentPending: explicit accept or scheduled conversion eligible
    TrialExpiring --> Expired: no valid conversion
    PaymentPending --> PaidPendingProvisioning: subscription verified server-side
    PaidPendingProvisioning --> Active: exact provisioning completed
    PaidPendingProvisioning --> Failed: provisioning exhausted
    Active --> PlanChangePending: new versioned plan requested
    PlanChangePending --> Active: new billing and provisioning atomically activated
    Active --> Suspended: provider-verified suspension
    Active --> Cancelled: provider-verified cancellation
    Suspended --> Active: provider-verified reactivation
    Suspended --> Expired: entitlement end reached
```

`PaymentPending` and `PaidPendingProvisioning` are intentionally separate. An
account is not active until both billing and tenant provisioning are verified.

## Subscription confirmation

```mermaid
sequenceDiagram
    participant U as Authenticated account
    participant P as Portal
    participant B as Billing adapter
    participant E as Event inbox
    participant O as Provisioning outbox
    participant D as Deployment authority
    U->>P: choose versioned plan or conversion
    P->>B: create/inspect provider subscription with tenant reference
    B-->>P: opaque billing reference
    P->>B: server-side get subscription
    B-->>P: signed/provider-authenticated plan amount currency status tenant
    P->>P: compare exact offer and account/tenant binding
    P->>E: store verified idempotent event digest
    E->>O: enqueue exact account tenant plan deployment reference once
    O->>D: request deployment plan and external grant
    D-->>O: verified resource reference or typed failure
    O-->>P: lifecycle transition receipt
```

A browser SDK success callback may initiate the `get subscription` step. It
cannot skip it or construct the verified event.

## Webhook/event processing

```mermaid
flowchart TD
    Input[Provider event] --> Headers{Required signature metadata?}
    Headers -->|no| Reject[Reject without state transition]
    Headers -->|yes| Verify[Provider verification API or local signature verifier]
    Verify -->|red/unknown| Reject
    Verify -->|green| Dedup{Event/idempotency key exists?}
    Dedup -->|yes| Same[Return prior receipt; no replay]
    Dedup -->|no| Bind[Bind provider plan tenant amount currency]
    Bind -->|mismatch| Quarantine[Store evidence and needs-human outcome]
    Bind -->|exact| Transition[Apply declared state transition]
    Transition --> Queue{Provisioning required?}
    Queue -->|yes| Outbox[Insert one idempotent outbox item]
    Queue -->|no| Receipt[Emit receipt]
    Outbox --> Receipt
```

Event ordering is provider-specific, but a conforming adapter MUST make stale
or contradictory events explicit. It cannot let an older activation override a
newer cancellation without a verified provider state lookup.

## Provisioning and plan change

```mermaid
sequenceDiagram
    participant L as Lifecycle store
    participant O as Outbox worker
    participant C as POA compiler
    participant A as Deployment authority
    participant X as Deployment executor
    participant V as Verifier
    L->>O: pending item with stable idempotency key
    O->>C: account tenant plan deployment refs
    C-->>O: exact plan hash
    O->>A: request single-use grant
    A-->>X: grant or denial
    X->>V: apply and verify immutable tenant release
    V-->>O: deployment receipt and resource ref
    O->>L: complete same outbox item
    L->>L: activate entitlements atomically
```

Retries reuse the same outbox item and deployment idempotency key. A failed
attempt increments its bounded attempt counter and records an evidence
reference, not a raw exception containing secrets.

## Failure routing

| Failure | Required state/outcome | Safe next action |
| --- | --- | --- |
| Missing trial conversion policy | `denied` | publish a new offer version |
| UI says paid without server verification | `billing_pending` | query provider server-side |
| Unsigned or invalid webhook | `denied` | reject and audit digest |
| Duplicate event | prior receipt | no state transition or new outbox item |
| Plan/amount/currency/tenant mismatch | `failed` or quarantine | reconcile with provider evidence |
| Billing verified, provisioning pending | `paid_pending_provisioning` | process durable outbox |
| Provisioning failed | `failed` | bounded retry or human remediation |
| Plan change partially completed | `plan_change_pending` | retain old active entitlements |
| Trial ends without eligible conversion | `expired` | require a new explicit selection |

No failure path stores payment credentials or turns a transport-level success
into an active tenant.
