"""Adapter profile validators for SaaS lifecycle v1."""

from __future__ import annotations

import re
from typing import Any

from saas_contracts import (
    PROFILE_SCHEMA_URI,
    UNSAFE_POINTER_SEGMENT,
    ContractError,
    Contracts,
    exact,
    is_int,
    reject_sensitive,
    unique_str_list,
)

URI_RE = re.compile(r"^[a-z][a-z0-9+.-]*://\S+$")
PROFILE_REF_RE = re.compile(r"^profile://\S+/v[0-9]+$")
ADAPTER_REF_RE = re.compile(r"^adapter://\S+/v[0-9]+$")
PROVIDER_REF_RE = re.compile(r"^provider://\S+(?:/v[0-9]+)?$")
POINTER_RE = re.compile(r"^(?:/(?:[^~/]|~0|~1)*)+$")
OP_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PROVIDER_EVENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{2,127}$")

SOURCE_FIELDS = {
    "accountRef", "tenantRef", "planRef", "priceRef", "providerPlanRef", "amountMinor",
    "currency", "billingRef", "providerResourceId", "requestId", "eventRef", "deploymentRef",
    "planHash", "grantRef", "idempotencyKey",
}
EVIDENCE_FIELDS = {
    "accountRef", "tenantRef", "planRef", "priceRef", "providerPlanRef", "amountMinor",
    "currency", "billingRef", "providerStatus", "requestId", "eventRef", "eventType",
    "occurredAt", "deploymentRef", "planHash", "grantRef", "resourceRef", "evidenceRef",
}
TRANSFORMS = {
    "identity", "registry-lookup", "minor-to-decimal-string", "decimal-string-to-minor",
    "uppercase", "lowercase", "opaque-reference", "unix-seconds-to-date-time", "sha256",
}


def uri(value: Any, pattern: re.Pattern[str] = URI_RE, max_len: int = 512) -> str:
    if not isinstance(value, str) or len(value) > max_len or pattern.fullmatch(value) is None:
        raise ContractError("invalid URI reference")
    return value


def safe_pointer(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 384 or POINTER_RE.fullmatch(value) is None:
        raise ContractError("invalid JSON Pointer")
    for encoded in value.split("/")[1:]:
        segment = encoded.replace("~1", "/").replace("~0", "~")
        if UNSAFE_POINTER_SEGMENT.fullmatch(segment):
            raise ContractError("unsafe pointer channel")
    return value


def retry_policy(value: Any) -> None:
    value = exact(value, {"maxAttempts", "backoff", "retryableOutcomes", "terminalOutcomes"})
    if not is_int(value["maxAttempts"]) or not 1 <= value["maxAttempts"] <= 20:
        raise ContractError("unbounded adapter retries")
    if value["backoff"] not in {"none", "bounded-exponential"}:
        raise ContractError("invalid adapter backoff")
    retryable = {"timeout", "rate-limited", "provider-unavailable", "pending"}
    terminal = {"verified", "denied", "failed", "cancelled", "exhausted"}
    r_items = unique_str_list(
        value["retryableOutcomes"], min_items=0, max_items=8, label="retryableOutcomes"
    )
    t_items = unique_str_list(
        value["terminalOutcomes"], min_items=2, max_items=5, label="terminalOutcomes"
    )
    if not set(r_items) <= retryable:
        raise ContractError("invalid retry outcomes")
    if not {"verified", "denied", "failed"} <= set(t_items) <= terminal:
        raise ContractError("invalid terminal outcomes")


def evidence_policy(value: Any) -> None:
    value = exact(
        value, {"providerPayload", "lifecycleReceipt", "authorizationMaterial", "personalData"}
    )
    expected = {
        "providerPayload": "separate-evidence-store",
        "lifecycleReceipt": "references-and-digests-only",
        "authorizationMaterial": "external-binding-only",
        "personalData": "minimized",
    }
    if value != expected:
        raise ContractError("unsafe adapter evidence policy")


def adapter_operation(value: Any) -> tuple[str, str]:
    req = {"id", "effect", "contractRef", "requestMappings", "evidenceMappings", "idempotency"}
    value = exact(value, req)
    if (
        not isinstance(value["id"], str)
        or len(value["id"]) > 96
        or OP_ID_RE.fullmatch(value["id"]) is None
    ):
        raise ContractError("invalid operation id")
    if value["effect"] not in {"query", "command", "verification"}:
        raise ContractError("invalid operation effect")
    uri(value["contractRef"])
    if not isinstance(value["requestMappings"], list) or len(value["requestMappings"]) > 20:
        raise ContractError("invalid request mappings")
    request_targets: set[str] = set()
    for mapping in value["requestMappings"]:
        mapping = exact(mapping, {"source", "targetPointer", "transform"})
        target = safe_pointer(mapping["targetPointer"])
        if target in request_targets:
            raise ContractError("duplicate request mapping")
        request_targets.add(target)
        if mapping["source"] not in SOURCE_FIELDS:
            raise ContractError("invalid request source")
        if mapping["transform"] not in TRANSFORMS:
            raise ContractError("invalid mapping transform")
    if not isinstance(value["evidenceMappings"], list) or not (
        1 <= len(value["evidenceMappings"]) <= 24
    ):
        raise ContractError("operation lacks evidence mapping")
    evidence_targets: set[str] = set()
    sources = {
        "provider-response", "verified-event", "provider-plan-registry",
        "request-ledger", "deployment-verifier",
    }
    for mapping in value["evidenceMappings"]:
        mapping = exact(mapping, {"sourceKind", "sourcePointer", "target", "transform"})
        safe_pointer(mapping["sourcePointer"])
        if mapping["sourceKind"] not in sources:
            raise ContractError("invalid evidence source")
        if mapping["target"] in evidence_targets:
            raise ContractError("duplicate evidence mapping")
        evidence_targets.add(mapping["target"])
        if mapping["target"] not in EVIDENCE_FIELDS:
            raise ContractError("invalid evidence target")
        if mapping["transform"] not in TRANSFORMS:
            raise ContractError("invalid evidence transform")
    idem = exact(value["idempotency"], {"required", "keySource"})
    if type(idem["required"]) is not bool or idem["keySource"] not in {
        "none", "request-id", "event-id", "outbox-id"
    }:
        raise ContractError("invalid idempotency binding")
    if value["effect"] in {"command", "verification"} and (
        idem["required"] is not True or idem["keySource"] == "none"
    ):
        raise ContractError("mutating operation lacks idempotency")
    if value["effect"] == "query" and (idem["required"] is not False or idem["keySource"] != "none"):
        raise ContractError("query has mutating idempotency")
    return value["id"], value["effect"]


def validate_payment_profile(_c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    req = {
        "$schema", "schema", "profileRef", "version", "adapterRef", "providerRef",
        "upstreamContracts", "operations", "requiredBindings", "eventBindings",
        "verification", "reconciliation", "retryPolicy", "evidencePolicy",
    }
    value = exact(value, req)
    if (
        value["$schema"] != PROFILE_SCHEMA_URI
        or value["schema"] != "wellmanifest.saas-payment-adapter-profile/v1"
    ):
        raise ContractError("unsupported payment profile")
    uri(value["profileRef"], PROFILE_REF_RE, 256)
    uri(value["adapterRef"], ADAPTER_REF_RE, 256)
    uri(value["providerRef"], PROVIDER_REF_RE, 256)
    if not isinstance(value["version"], str) or VERSION_RE.fullmatch(value["version"]) is None:
        raise ContractError("invalid profile version")
    for ref in unique_str_list(
        value["upstreamContracts"], min_items=1, max_items=12, label="upstreamContracts"
    ):
        uri(ref)
    if not isinstance(value["operations"], list) or not 7 <= len(value["operations"]) <= 12:
        raise ContractError("payment operation set incomplete")
    operations = dict(adapter_operation(item) for item in value["operations"])
    effects = {
        "create_subscription": "command", "inspect_subscription": "query",
        "cancel_subscription": "command", "create_payment": "command",
        "inspect_payment": "query", "capture_payment": "command", "verify_event": "verification",
    }
    if len(operations) != len(value["operations"]) or operations != effects:
        raise ContractError("payment operation effect mismatch")
    bindings = {
        "accountRef", "tenantRef", "planRef", "priceRef", "amountMinor", "currency", "providerStatus"
    }
    req_bindings = unique_str_list(
        value["requiredBindings"], min_items=7, max_items=7, label="requiredBindings"
    )
    if set(req_bindings) != bindings:
        raise ContractError("payment verification bindings incomplete")
    if not isinstance(value["eventBindings"], list) or not 4 <= len(value["eventBindings"]) <= 20:
        raise ContractError("payment event mappings incomplete")
    provider_events: set[str] = set()
    signals = {
        "reconcile_subscription", "reconcile_payment", "subscription_activated",
        "subscription_suspended", "subscription_cancelled", "addon_payment_completed",
        "payment_denied",
    }
    ev_req = {
        "providerEvent", "lifecycleSignal", "eventIdPointer", "resourcePointer", "requiresInspection"
    }
    for item in value["eventBindings"]:
        item = exact(item, ev_req)
        pev = item["providerEvent"]
        if (
            not isinstance(pev, str)
            or PROVIDER_EVENT_RE.fullmatch(pev) is None
            or pev in provider_events
        ):
            raise ContractError("duplicate or invalid provider event")
        provider_events.add(pev)
        safe_pointer(item["eventIdPointer"])
        safe_pointer(item["resourcePointer"])
        if item["lifecycleSignal"] not in signals:
            raise ContractError("invalid lifecycle signal")
        if item["requiresInspection"] is not True:
            raise ContractError("provider event trusted without inspection")
    ver_req = {
        "mode", "contractRef", "operationId", "requiredInputs",
        "successPredicate", "failureOutcome", "payloadRetention",
    }
    ver = exact(value["verification"], ver_req)
    uri(ver["contractRef"])
    if (
        ver["mode"] not in {"provider-api", "local-signature"}
        or ver["operationId"] != "verify_event"
        or ver["failureOutcome"] != "denied"
        or ver["payloadRetention"] != "digest-only"
    ):
        raise ContractError("unsafe event verification")
    inputs = set(
        unique_str_list(ver["requiredInputs"], min_items=3, max_items=4, label="requiredInputs")
    )
    allowed_in = {
        "raw-body", "transport-signature",
        "configured-verifier-binding", "provider-certificate-metadata",
    }
    if not (
        {"raw-body", "transport-signature", "configured-verifier-binding"} <= inputs <= allowed_in
    ):
        raise ContractError("verification inputs incomplete")
    predicate = exact(ver["successPredicate"], {"source", "equals"}, {"pointer"})
    if predicate["source"] == "operation-result":
        if (
            "pointer" not in predicate
            or safe_pointer(predicate["pointer"]) != "/verification_status"
            or predicate["equals"] != "SUCCESS"
        ):
            raise ContractError("invalid provider verification predicate")
    elif predicate["source"] == "verified-call-return":
        if "pointer" in predicate or predicate["equals"] != "verified":
            raise ContractError("invalid local verification predicate")
    else:
        raise ContractError("unsupported verification predicate")
    rec_req = {
        "subscriptionInspectOperationId", "paymentInspectOperationId",
        "unknownEventOutcome", "outOfOrder", "staleEvent",
    }
    reconciliation = exact(value["reconciliation"], rec_req)
    if reconciliation != {
        "subscriptionInspectOperationId": "inspect_subscription",
        "paymentInspectOperationId": "inspect_payment",
        "unknownEventOutcome": "quarantine",
        "outOfOrder": "inspect-authoritative-resource",
        "staleEvent": "no-transition",
    }:
        raise ContractError("unsafe payment reconciliation")
    retry_policy(value["retryPolicy"])
    evidence_policy(value["evidencePolicy"])


def validate_deployment_profile(_c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    req = {
        "$schema", "schema", "profileRef", "version", "adapterRef", "upstreamContracts",
        "operations", "requiredBindings", "authorization", "activationBoundary", "outbox",
        "coordinatePolicy", "retryPolicy", "evidencePolicy",
    }
    value = exact(value, req)
    if (
        value["$schema"] != PROFILE_SCHEMA_URI
        or value["schema"] != "wellmanifest.saas-deployment-adapter-profile/v1"
    ):
        raise ContractError("unsupported deployment profile")
    uri(value["profileRef"], PROFILE_REF_RE, 256)
    uri(value["adapterRef"], ADAPTER_REF_RE, 256)
    if not isinstance(value["version"], str) or VERSION_RE.fullmatch(value["version"]) is None:
        raise ContractError("invalid profile version")
    for ref in unique_str_list(
        value["upstreamContracts"], min_items=1, max_items=12, label="upstreamContracts"
    ):
        uri(ref)
    if not isinstance(value["operations"], list) or not 5 <= len(value["operations"]) <= 8:
        raise ContractError("deployment operation set incomplete")
    operations = dict(adapter_operation(item) for item in value["operations"])
    effects = {
        "compile": "query", "authorize": "command", "apply": "command",
        "verify": "verification", "rollback": "command",
    }
    if len(operations) != len(value["operations"]) or operations != effects:
        raise ContractError("deployment operation set incomplete")
    bindings = {
        "accountRef", "tenantRef", "planRef", "deploymentRef",
        "planHash", "grantRef", "idempotencyKey",
    }
    req_bindings = unique_str_list(
        value["requiredBindings"], min_items=7, max_items=7, label="requiredBindings"
    )
    if set(req_bindings) != bindings:
        raise ContractError("deployment bindings incomplete")
    auth = exact(value["authorization"], {"mode", "operationId", "persistGrant", "denialOutcome"})
    if auth != {
        "mode": "single-use-external-grant",
        "operationId": "authorize",
        "persistGrant": False,
        "denialOutcome": "denied",
    }:
        raise ContractError("unsafe deployment authorization")
    act_req = {"requiresApplyAndVerify", "verifyOperationId", "successOutcome", "mismatchOutcome"}
    act = exact(value["activationBoundary"], act_req)
    if act != {
        "requiresApplyAndVerify": True,
        "verifyOperationId": "verify",
        "successOutcome": "activated",
        "mismatchOutcome": "failed",
    }:
        raise ContractError("unsafe deployment activation")
    outbox = exact(value["outbox"], {"durable", "reuseIdempotencyKey", "claimMode"})
    if outbox != {
        "durable": True,
        "reuseIdempotencyKey": True,
        "claimMode": "single-worker-lease",
    }:
        raise ContractError("unsafe deployment outbox")
    coords = exact(value["coordinatePolicy"], {"profileContainsCoordinates", "resolution", "receipt"})
    if coords != {
        "profileContainsCoordinates": False,
        "resolution": "external-deployment-binding",
        "receipt": "resource-reference-only",
    }:
        raise ContractError("raw deployment coordinates")
    retry_policy(value["retryPolicy"])
    evidence_policy(value["evidencePolicy"])


def validate_profile_examples(c: Contracts) -> list[dict[str, Any]]:
    examples = exact(c.profile_examples, {"schema", "profiles"})
    if (
        examples["schema"] != "wellmanifest.saas-adapter-profile-examples/v1"
        or not isinstance(examples["profiles"], list)
    ):
        raise ContractError("invalid profile examples")
    profile_refs: set[str] = set()
    adapter_refs: set[str] = set()
    providers: set[str] = set()
    deployment_count = 0
    for profile in examples["profiles"]:
        if not isinstance(profile, dict):
            raise ContractError("invalid profile example")
        if profile.get("schema") == "wellmanifest.saas-payment-adapter-profile/v1":
            validate_payment_profile(c, profile)
            providers.add(profile["providerRef"])
        elif profile.get("schema") == "wellmanifest.saas-deployment-adapter-profile/v1":
            validate_deployment_profile(c, profile)
            deployment_count += 1
        else:
            raise ContractError("unknown profile example")
        if profile["profileRef"] in profile_refs or profile["adapterRef"] in adapter_refs:
            raise ContractError("duplicate adapter profile identity")
        profile_refs.add(profile["profileRef"])
        adapter_refs.add(profile["adapterRef"])
    if len(providers) < 2 or deployment_count < 1:
        raise ContractError("provider neutrality evidence incomplete")
    return examples["profiles"]
