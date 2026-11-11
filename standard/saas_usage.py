"""Execution receipt and usage ledger validators for SaaS lifecycle v1."""

from __future__ import annotations

from typing import Any

from saas_contracts import (
    SCHEMA_URI,
    ContractError,
    Contracts,
    exact,
    is_int,
    reject_sensitive,
    time_value,
    unique_str_list,
)

RECEIPT_OUTCOMES = {
    "denied", "accepted", "trial_started", "billing_pending", "billing_verified",
    "provisioning_queued", "activated", "addon_activated", "cancelled", "failed",
}


def validate_receipt(c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    req = {
        "$schema", "schema", "requestId", "accountRef", "tenantRef", "planRef", "priceRef",
        "inputHash", "planHash", "outcome", "startedAt", "completedAt", "evidenceRefs",
        "secretsRedacted", "paymentDataStored",
    }
    value = exact(value, req)
    if value["$schema"] != SCHEMA_URI or value["schema"] != "wellmanifest.saas-lifecycle-receipt/v1":
        raise ContractError("unsupported receipt")
    for name, field in (
        ("identifier", "requestId"), ("accountRef", "accountRef"), ("tenantRef", "tenantRef"),
        ("planRef", "planRef"), ("priceRef", "priceRef"), ("sha256", "inputHash"),
        ("sha256", "planHash"),
    ):
        c.ref(name, value[field])
    if time_value(value["completedAt"]) < time_value(value["startedAt"]):
        raise ContractError("receipt chronology")
    if value["outcome"] not in RECEIPT_OUTCOMES:
        raise ContractError("unsupported receipt outcome")
    for ref in unique_str_list(value["evidenceRefs"], min_items=1, max_items=64, label="evidenceRefs"):
        c.ref("evidenceRef", ref)
    if value["secretsRedacted"] is not True or value["paymentDataStored"] is not False:
        raise ContractError("unsafe receipt")


def validate_usage_entry(c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    required = {
        "$schema", "schema", "entryRef", "idempotencyKey", "kind", "accountRef", "tenantRef",
        "sourcePlanRef", "priceRef", "usageGrantRef", "metricRef", "meteringRuleRef",
        "attribution", "authority", "measurement", "ledgerUnits", "operationOutcome",
        "recordedAt", "evidenceRefs", "secretsRedacted", "paymentDataStored",
    }
    value = exact(value, required, {"relatedEntryRef"})
    if (
        value["$schema"] != SCHEMA_URI
        or value["schema"] != "wellmanifest.saas-usage-ledger-entry/v1"
    ):
        raise ContractError("unsupported usage entry")
    for name, field in (
        ("usageEntryRef", "entryRef"), ("identifier", "idempotencyKey"), ("accountRef", "accountRef"),
        ("tenantRef", "tenantRef"), ("planRef", "sourcePlanRef"), ("priceRef", "priceRef"),
        ("grantRef", "usageGrantRef"), ("metricRef", "metricRef"), ("meteringRuleRef", "meteringRuleRef"),
    ):
        c.ref(name, value[field])
    kind = value["kind"]
    if kind not in {"reserve", "settle", "release", "waive", "refund"}:
        raise ContractError("unsupported usage entry kind")
    if "relatedEntryRef" in value:
        c.ref("usageEntryRef", value["relatedEntryRef"])
        if value["relatedEntryRef"] == value["entryRef"]:
            raise ContractError("usage entry cannot relate to itself")
    if kind in {"settle", "release", "refund"} and "relatedEntryRef" not in value:
        raise ContractError("usage entry lacks prior entry binding")
    if kind == "reserve" and "relatedEntryRef" in value:
        raise ContractError("reservation cannot have a prior entry")

    attr_req = {
        "organizationRef", "projectRef", "ticketRef", "principalRef",
        "processRunRef", "attemptRef", "uriProcessRef", "operationClassRef",
    }
    attribution = exact(value["attribution"], attr_req)
    c.ref("organizationRef", attribution["organizationRef"])
    for name in ("projectRef", "ticketRef"):
        if attribution[name] is not None:
            c.ref(name, attribution[name])
    for name in ("principalRef", "processRunRef", "attemptRef", "uriProcessRef", "operationClassRef"):
        c.ref(name, attribution[name])

    authority = exact(
        value["authority"], {"decisionRef", "authorityGrantRef", "leaseRef", "delegationDigest"}
    )
    c.ref("evidenceRef", authority["decisionRef"])
    for name, field in (
        ("authorityGrantRef", "authorityGrantRef"),
        ("leaseRef", "leaseRef"),
        ("sha256Ref", "delegationDigest"),
    ):
        if authority[field] is not None:
            c.ref(name, authority[field])

    measurement = exact(
        value["measurement"], {"kind", "observedUnits", "billableUnits", "calculationDigest"}
    )
    if measurement["kind"] not in {"estimate", "actual", "not-applicable"}:
        raise ContractError("unsupported measurement kind")
    if any(
        not is_int(measurement[name]) or not 0 <= measurement[name] <= 1_000_000_000_000
        for name in ("observedUnits", "billableUnits")
    ):
        raise ContractError("invalid measured units")
    c.ref("sha256Ref", measurement["calculationDigest"])
    units, outcome = value["ledgerUnits"], value["operationOutcome"]
    if not is_int(units) or not 0 <= units <= 1_000_000_000_000:
        raise ContractError("invalid ledger units")
    if kind == "reserve":
        if (
            measurement["kind"] != "estimate"
            or units < 1
            or units != measurement["billableUnits"]
            or outcome != "pending"
        ):
            raise ContractError("invalid reservation")
    elif kind == "settle":
        if (
            measurement["kind"] != "actual"
            or units < 1
            or units != measurement["billableUnits"]
            or outcome == "pending"
        ):
            raise ContractError("invalid settlement")
    elif kind == "waive":
        if measurement["kind"] != "actual" or units != 0 or outcome == "pending":
            raise ContractError("invalid waiver")
    elif (
        measurement["kind"] != "not-applicable"
        or measurement["observedUnits"] != 0
        or measurement["billableUnits"] != 0
        or units < 1
        or outcome == "pending"
    ):
        raise ContractError("invalid release or refund")
    if outcome not in {"pending", "succeeded", "failed", "denied", "cancelled"}:
        raise ContractError("unsupported operation outcome")
    if outcome in {"succeeded", "failed"} and authority["authorityGrantRef"] is None:
        raise ContractError("execution outcome lacks authority grant")
    time_value(value["recordedAt"])
    for reference in unique_str_list(value["evidenceRefs"], min_items=1, max_items=64, label="evidenceRefs"):
        c.ref("evidenceRef", reference)
    if value["secretsRedacted"] is not True or value["paymentDataStored"] is not False:
        raise ContractError("unsafe usage entry")


def project_usage_ledger(
    c: Contracts, entries: list[dict[str, Any]], initial_units: int
) -> dict[str, int]:
    if not isinstance(entries, list):
        raise ContractError("invalid usage ledger entries")
    if not is_int(initial_units) or initial_units < 0:
        raise ContractError("invalid initial usage balance")
    available, consumed = initial_units, 0
    reserved: dict[str, int] = {}
    settled: dict[str, int] = {}
    by_ref: dict[str, dict[str, Any]] = {}
    keys: set[str] = set()
    for entry in entries:
        validate_usage_entry(c, entry)
        ref, key, kind = entry["entryRef"], entry["idempotencyKey"], entry["kind"]
        if ref in by_ref or key in keys:
            raise ContractError("usage ledger replay")
        related = by_ref.get(entry.get("relatedEntryRef"))
        if entry.get("relatedEntryRef") is not None and related is None:
            raise ContractError("unresolved usage relation")
        if related is not None:
            for field in ("accountRef", "tenantRef", "usageGrantRef", "metricRef", "meteringRuleRef"):
                if entry[field] != related[field]:
                    raise ContractError("cross-boundary usage relation")
            for field in (
                "organizationRef", "projectRef", "ticketRef",
                "processRunRef", "attemptRef", "uriProcessRef",
            ):
                if entry["attribution"][field] != related["attribution"][field]:
                    raise ContractError("cross-attribution usage relation")
        units = entry["ledgerUnits"]
        if kind == "reserve":
            if units > available:
                raise ContractError("usage allowance overdraw")
            available -= units
            reserved[ref] = units
        elif kind == "settle":
            source = entry["relatedEntryRef"]
            if related is None or related["kind"] != "reserve" or units > reserved.get(source, 0):
                raise ContractError("settlement exceeds reservation")
            reserved[source] -= units
            consumed += units
            settled[ref] = units
        elif kind == "release":
            source = entry["relatedEntryRef"]
            if related is None or related["kind"] != "reserve" or units > reserved.get(source, 0):
                raise ContractError("release exceeds reservation")
            reserved[source] -= units
            available += units
        elif kind == "refund":
            source = entry["relatedEntryRef"]
            if related is None or related["kind"] != "settle" or units > settled.get(source, 0):
                raise ContractError("refund exceeds settlement")
            settled[source] -= units
            consumed -= units
            available += units
        by_ref[ref] = entry
        keys.add(key)
    return {
        "initialUnits": initial_units,
        "availableUnits": available,
        "reservedUnits": sum(reserved.values()),
        "consumedUnits": consumed,
        "entryCount": len(by_ref),
    }
