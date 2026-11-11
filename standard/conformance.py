#!/usr/bin/env python3
"""Dependency-free conformance checks for SaaS lifecycle v1."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path
from typing import Any

from saas_contracts import (
    GRAMMAR_DIGEST,
    GRAMMAR_PATH,
    LIFECYCLE_PATH,
    LIFECYCLE_PROFILE_DIGEST,
    LIFECYCLE_SOURCE_REVISION,
    LIFECYCLE_TRANSITIONS,
    LIFECYCLE_VALIDATOR_DIGEST,
    LIFECYCLE_VALIDATOR_PATH,
    PROFILE_EXAMPLES_DIGEST,
    PROFILE_EXAMPLES_PATH,
    PROFILE_SCHEMA_DIGEST,
    PROFILE_SCHEMA_PATH,
    PROFILE_SCHEMA_URI,
    ROOT,
    SCHEMA_DIGEST,
    SCHEMA_PATH,
    SCHEMA_URI,
    ContractError,
    Contracts,
    canonical,
    digest,
    exact,
    file_digest,
    lifecycle_name,
    reject_no_symlink,
    reject_sensitive,
    strict_json_load,
    time_value,
    validate_lifecycle_profile,
)
from saas_examples import (
    lifecycle_example,
    offer_example,
    receipt_example,
    request_example,
    usage_entry_example,
    usage_ledger_example,
)
from saas_profiles import (
    adapter_operation,
    evidence_policy,
    retry_policy,
    safe_pointer,
    uri,
    validate_deployment_profile,
    validate_payment_profile,
    validate_profile_examples,
)
from saas_usage import project_usage_ledger, validate_receipt, validate_usage_entry
from saas_validators import (
    prepaid_allowance,
    recurring_allowance,
    settlement,
    validate_lifecycle,
    validate_offer,
    validate_request,
)

__all__ = [
    "GRAMMAR_DIGEST",
    "GRAMMAR_PATH",
    "LIFECYCLE_PATH",
    "LIFECYCLE_PROFILE_DIGEST",
    "LIFECYCLE_SOURCE_REVISION",
    "LIFECYCLE_TRANSITIONS",
    "LIFECYCLE_VALIDATOR_DIGEST",
    "LIFECYCLE_VALIDATOR_PATH",
    "PROFILE_EXAMPLES_DIGEST",
    "PROFILE_EXAMPLES_PATH",
    "PROFILE_SCHEMA_DIGEST",
    "PROFILE_SCHEMA_PATH",
    "PROFILE_SCHEMA_URI",
    "ROOT",
    "SCHEMA_DIGEST",
    "SCHEMA_PATH",
    "SCHEMA_URI",
    "ContractError",
    "Contracts",
    "adapter_operation",
    "canonical",
    "digest",
    "evidence_policy",
    "exact",
    "file_digest",
    "lifecycle_example",
    "lifecycle_name",
    "main",
    "offer_example",
    "prepaid_allowance",
    "project_usage_ledger",
    "receipt_example",
    "recurring_allowance",
    "reject_no_symlink",
    "reject_sensitive",
    "request_example",
    "retry_policy",
    "run_all",
    "safe_pointer",
    "settlement",
    "strict_json_load",
    "time_value",
    "uri",
    "usage_entry_example",
    "usage_ledger_example",
    "validate_deployment_profile",
    "validate_lifecycle",
    "validate_lifecycle_profile",
    "validate_offer",
    "validate_payment_profile",
    "validate_profile_examples",
    "validate_receipt",
    "validate_request",
    "validate_usage_entry",
]

OWNED_MODULES = (
    "conformance.py",
    "saas_contracts.py",
    "saas_validators.py",
    "saas_usage.py",
    "saas_examples.py",
    "saas_profiles.py",
)


def _check_module_line_budgets() -> None:
    for mod in OWNED_MODULES:
        lines = len((ROOT / mod).read_text(encoding="utf-8").splitlines())
        if lines >= 500:
            raise ContractError(f"module exceeds 500-line ceiling: {mod} ({lines})")


def _check_loader_adversarial() -> list[str]:
    names: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        dup = base / "dup.json"
        dup.write_text('{"a": 1, "a": 2}\n', encoding="utf-8")
        try:
            strict_json_load(dup)
        except ContractError:
            names.append("duplicate-json-key")
        else:
            raise AssertionError("adversarial case accepted: duplicate-json-key")

        target = base / "real.json"
        target.write_text('{"ok": true}\n', encoding="utf-8")
        link = base / "link.json"
        link.symlink_to(target)
        try:
            strict_json_load(link)
        except ContractError:
            names.append("symlinked-contract-file")
        else:
            raise AssertionError("adversarial case accepted: symlinked-contract-file")
    return names


def _build_adversarial_cases(
    c: Contracts,
    offer: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    receipt: dict[str, Any],
    usage: dict[str, Any],
    paypal: dict[str, Any],
    stripe: dict[str, Any],
    deployment: dict[str, Any],
) -> list[tuple[str, Any]]:
    cases: list[tuple[str, Any]] = []

    def add(name: str, validator: Any, value: Any) -> None:
        cases.append((name, lambda validator=validator, value=value: validator(c, value)))

    def mut(base: dict[str, Any], fn: Any) -> dict[str, Any]:
        val = copy.deepcopy(base)
        fn(val)
        return val

    add("trial-no-conversion", validate_offer, mut(offer, lambda d: d["plans"][0]["trial"].pop("conversionPlanRef")))
    add("trial-no-cancel-boundary", validate_offer, mut(offer, lambda d: d["plans"][0]["trial"].__setitem__("cancelBeforeCharge", False)))
    add("scheduled-no-payment-method", validate_offer, mut(offer, lambda d: d["plans"][0]["trial"].__setitem__("conversionMode", "scheduled-after-notice")))
    add("authoritative-display-rate", validate_offer, mut(offer, lambda d: d["displayQuotes"][0].__setitem__("indicative", False)))
    add("false-capability-parity", validate_offer, mut(offer, lambda d: d["plans"][2].__setitem__("entitlements", ["entitlement://example.test/subactor/pro-only/v1"])))
    add("recurring-prepaid-charge", validate_offer, mut(offer, lambda d: d["plans"][3]["settlements"][0].__setitem__("interval", "month")))
    add(
        "duplicate-billing-interval",
        validate_offer,
        mut(offer, lambda d: d["plans"][1]["settlements"].append({**copy.deepcopy(d["plans"][1]["settlements"][0]), "priceRef": "price://example.test/basic/month-promo/v1"})),
    )
    add("duplicate-price-reference", validate_offer, mut(offer, lambda d: d["plans"][2]["settlements"][0].__setitem__("priceRef", "price://example.test/basic/month/v1")))
    add("prepaid-without-expiry", validate_offer, mut(offer, lambda d: d["plans"][3]["commercial"]["usageAllowance"].pop("validityDays")))
    add("prepaid-targets-flat-plan", validate_offer, mut(offer, lambda d: d["plans"][3]["commercial"].__setitem__("compatiblePlanRefs", ["plan://example.test/trial/v1"])))
    add("prepaid-metric-mismatch", validate_offer, mut(offer, lambda d: d["plans"][3]["commercial"]["usageAllowance"].__setitem__("metricRef", "metric://example.test/api/calls/v1")))
    add("cloud-perpetual-license", validate_offer, mut(offer, lambda d: d["plans"][4].__setitem__("deploymentMode", "cloud")))
    add("duplicate-locale-default", validate_offer, mut(offer, lambda d: d["localeDefaults"].append({"locale": "pl", "currency": "EUR"})))
    add("missing-display-coverage", validate_offer, mut(offer, lambda d: d["displayQuotes"].pop()))
    add("duplicate-display-pair", validate_offer, mut(offer, lambda d: d["displayQuotes"].append(copy.deepcopy(d["displayQuotes"][0]))))
    add("identity-display-rate", validate_offer, mut(offer, lambda d: d["displayQuotes"][0].__setitem__("quoteCurrency", "PLN")))
    add("bool-recurring-units", validate_offer, mut(offer, lambda d: d["plans"][1]["commercial"]["usageAllowance"].__setitem__("includedUnits", True)))
    add("bool-prepaid-validity", validate_offer, mut(offer, lambda d: d["plans"][3]["commercial"]["usageAllowance"].__setitem__("validityDays", True)))
    add("bool-display-rate", validate_offer, mut(offer, lambda d: d["displayQuotes"][0].__setitem__("rateNumerator", True)))
    add("bool-trial-days", validate_offer, mut(offer, lambda d: d["plans"][0]["trial"].__setitem__("days", True)))
    add("invalid-offer-version", validate_offer, mut(offer, lambda d: d.__setitem__("version", "v1")))
    add("invalid-legal-policy-ref", validate_offer, mut(offer, lambda d: d.__setitem__("legalPolicyRef", "https://example.test/terms")))
    add("trial-notice-exceeds-duration", validate_offer, mut(offer, lambda d: d["plans"][0]["trial"].__setitem__("noticeDays", 30)))

    add("client-payment-status", validate_request, mut(request, lambda d: d.__setitem__("paymentStatus", "COMPLETED")))
    add("payment-credential", validate_request, mut(request, lambda d: d.__setitem__("card_token", "redacted-canary")))
    add("raw-tenant-coordinate", validate_request, mut(request, lambda d: d.__setitem__("hostname", "acme.example.test")))
    add("implicit-price-selection", validate_request, mut(request, lambda d: d.pop("priceRef")))
    add("inline-bearer-secret", validate_request, mut(request, lambda d: d.__setitem__("billingRef", "Bearer " + "x" * 24)))

    add("unsigned-event", validate_lifecycle, mut(state, lambda d: d["events"][0].__setitem__("signatureVerified", False)))
    add("duplicate-event", validate_lifecycle, mut(state, lambda d: d["events"].append(copy.deepcopy(d["events"][0]))))
    add("client-trusted-subscription", validate_lifecycle, mut(state, lambda d: d["subscription"].__setitem__("verificationMode", "browser-callback")))
    add("active-without-subscription", validate_lifecycle, mut(state, lambda d: d.pop("subscription")))
    add("active-before-provisioned", validate_lifecycle, mut(state, lambda d: (d["provisioning"].__setitem__("state", "pending"), d["provisioning"].pop("externalRef"))))
    add("unbounded-provisioning", validate_lifecycle, mut(state, lambda d: d["provisioning"].__setitem__("attempts", 21)))
    add("client-issued-usage-grant", validate_lifecycle, mut(state, lambda d: d["usageGrants"][0].__setitem__("verificationMode", "browser-callback")))
    add("usage-grant-overdraw", validate_lifecycle, mut(state, lambda d: d["usageGrants"][0].__setitem__("unitsRemaining", 10001)))
    add("usage-grant-invalid-expiry", validate_lifecycle, mut(state, lambda d: d["usageGrants"][0].__setitem__("expiresAt", "2026-08-11T11:58:00Z")))
    add("duplicate-usage-grant", validate_lifecycle, mut(state, lambda d: d["usageGrants"].append(copy.deepcopy(d["usageGrants"][0]))))
    add("bool-usage-grant-units", validate_lifecycle, mut(state, lambda d: d["usageGrants"][0].__setitem__("unitsGranted", True)))

    add("provider-payload-receipt", validate_receipt, mut(receipt, lambda d: d.__setitem__("providerPayload", {"status": "ACTIVE"})))
    add("payment-data-receipt", validate_receipt, mut(receipt, lambda d: d.__setitem__("paymentDataStored", True)))
    add("unhashable-receipt-evidence", validate_receipt, mut(receipt, lambda d: d.__setitem__("evidenceRefs", [{}])))

    add("usage-without-organization", validate_usage_entry, mut(usage, lambda d: d["attribution"].pop("organizationRef")))
    add("usage-implicit-attribution", validate_usage_entry, mut(usage, lambda d: d.__setitem__("projectRef", "project://example.test/guessed")))
    add("reservation-unit-mismatch", validate_usage_entry, mut(usage, lambda d: d.__setitem__("ledgerUnits", 2)))
    add("settlement-without-reservation", validate_usage_entry, mut(usage, lambda d: (d.update({"kind": "settle", "operationOutcome": "succeeded"}), d["measurement"].__setitem__("kind", "actual"))))
    add(
        "executed-usage-without-authority",
        validate_usage_entry,
        mut(usage, lambda d: (d["authority"].__setitem__("authorityGrantRef", None), d.update({"kind": "settle", "relatedEntryRef": "usage://example.test/entries/attempt-001/reserve", "operationOutcome": "succeeded"}), d["measurement"].__setitem__("kind", "actual"))),
    )
    add("waiver-that-debits", validate_usage_entry, mut(usage, lambda d: (d.update({"kind": "waive", "operationOutcome": "denied"}), d["measurement"].__setitem__("kind", "actual"))))
    add("usage-secret-channel", validate_usage_entry, mut(usage, lambda d: d["authority"].__setitem__("access_token", "redacted-canary")))
    add("unhashable-usage-evidence", validate_usage_entry, mut(usage, lambda d: d.__setitem__("evidenceRefs", [{}])))

    add("duplicate-payment-operation", validate_payment_profile, mut(paypal, lambda d: d["operations"].append(copy.deepcopy(d["operations"][0]))))
    add("payment-without-event-verifier", validate_payment_profile, mut(paypal, lambda d: d.__setitem__("operations", [i for i in d["operations"] if i["id"] != "verify_event"])))
    add("non-idempotent-payment-command", validate_payment_profile, mut(paypal, lambda d: d["operations"][0].__setitem__("idempotency", {"required": False, "keySource": "none"})))
    add("provider-verification-without-predicate", validate_payment_profile, mut(paypal, lambda d: d["verification"]["successPredicate"].pop("pointer")))
    add("duplicate-provider-event", validate_payment_profile, mut(paypal, lambda d: d["eventBindings"].append(copy.deepcopy(d["eventBindings"][0]))))
    add("unhashable-upstream-contracts", validate_payment_profile, mut(paypal, lambda d: d.__setitem__("upstreamContracts", [{}])))
    add("event-trusted-without-inspection", validate_payment_profile, mut(stripe, lambda d: d["eventBindings"][0].__setitem__("requiresInspection", False)))
    add("payment-secret-pointer", validate_payment_profile, mut(stripe, lambda d: d["operations"][3]["requestMappings"][0].__setitem__("targetPointer", "/card/number")))

    add("deployment-coordinate-pointer", validate_deployment_profile, mut(deployment, lambda d: d["operations"][2]["requestMappings"][0].__setitem__("targetPointer", "/hostname")))
    add("unbounded-adapter-retries", validate_deployment_profile, mut(deployment, lambda d: d["retryPolicy"].__setitem__("maxAttempts", 21)))
    add("persisted-deployment-grant", validate_deployment_profile, mut(deployment, lambda d: d["authorization"].__setitem__("persistGrant", True)))
    add("activation-without-verification", validate_deployment_profile, mut(deployment, lambda d: d["activationBoundary"].__setitem__("requiresApplyAndVerify", False)))
    add("non-durable-deployment-outbox", validate_deployment_profile, mut(deployment, lambda d: d["outbox"].__setitem__("durable", False)))
    add("provider-payload-in-lifecycle-receipt", validate_deployment_profile, mut(deployment, lambda d: d["evidencePolicy"].__setitem__("lifecycleReceipt", "raw-provider-payload")))
    add("unhashable-retry-outcomes", validate_deployment_profile, mut(deployment, lambda d: d["retryPolicy"].__setitem__("retryableOutcomes", [{}])))
    return cases


def run_all() -> dict[str, Any]:
    _check_module_line_budgets()
    c = Contracts()
    c.integrity()
    offer, request, state, receipt, usage = (
        offer_example(),
        request_example(),
        lifecycle_example(),
        receipt_example(),
        usage_entry_example(),
    )
    validate_lifecycle_profile(c.schema)
    validate_offer(c, offer)
    validate_request(c, request)
    validate_lifecycle(c, state)
    validate_receipt(c, receipt)
    validate_usage_entry(c, usage)
    ledger = usage_ledger_example()
    projection = project_usage_ledger(c, ledger, 10)
    if projection != {
        "initialUnits": 10,
        "availableUnits": 9,
        "reservedUnits": 0,
        "consumedUnits": 1,
        "entryCount": 5,
    }:
        raise AssertionError("usage projection mismatch")
    profiles = validate_profile_examples(c)
    paypal, stripe, deployment = profiles

    cases = _build_adversarial_cases(
        c, offer, request, state, receipt, usage, paypal, stripe, deployment
    )
    rejected: list[str] = []
    for name, case in cases:
        try:
            case()
        except ContractError:
            rejected.append(name)
        else:
            raise AssertionError(f"adversarial case accepted: {name}")

    def reject_ledger(name: str, entries: Any, initial: Any = 10) -> None:
        try:
            project_usage_ledger(c, entries, initial)
        except ContractError:
            rejected.append(name)
        else:
            raise AssertionError(f"adversarial ledger accepted: {name}")

    bad = copy.deepcopy(ledger)
    bad.append(copy.deepcopy(bad[0]))
    reject_ledger("usage-ledger-replay", bad)
    bad = copy.deepcopy(ledger)
    bad[0]["ledgerUnits"] = 11
    bad[0]["measurement"]["billableUnits"] = 11
    reject_ledger("usage-ledger-overdraw", bad)
    bad = copy.deepcopy(ledger)
    bad[1]["attribution"]["projectRef"] = "project://example.test/other"
    reject_ledger("usage-ledger-cross-attribution", bad)
    reject_ledger("usage-ledger-bool-initial", ledger, True)
    rejected.extend(_check_loader_adversarial())

    return {
        "schema": "wellmanifest.saas-lifecycle-conformance/v1",
        "ok": True,
        "schemaDigest": "sha256:" + SCHEMA_DIGEST,
        "grammarDigest": "sha256:" + GRAMMAR_DIGEST,
        "profileSchemaDigest": "sha256:" + PROFILE_SCHEMA_DIGEST,
        "profileExamplesDigest": "sha256:" + PROFILE_EXAMPLES_DIGEST,
        "positiveVariants": 5,
        "usageLedgerEntries": projection["entryCount"],
        "adapterProfileVariants": len(profiles),
        "adversarialRejected": rejected,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    if not args.all:
        p.error("--all is required")
    print(json.dumps(run_all(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
