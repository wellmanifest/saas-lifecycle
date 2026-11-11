"""Domain validators for SaaS lifecycle v1 offers, requests, state, receipts, and usage ledger."""

from __future__ import annotations

import re
from datetime import date
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

SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
POLICY_REF_RE = re.compile(r"^policy://[a-z0-9.-]+/[A-Za-z0-9._:/-]+/v[1-9][0-9]*$")
RESOURCE_REF_RE = re.compile(r"^resource://[a-z0-9.-]+/[A-Za-z0-9._:/-]+$")
LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")

LIFECYCLE_STATES = {
    "requested", "membership_verified", "trial_active", "trial_expiring", "payment_pending",
    "paid_pending_provisioning", "active", "plan_change_pending", "suspended", "cancelled",
    "expired", "failed",
}
BILLING_EVENT_TYPES = {
    "subscription_activated", "subscription_suspended", "subscription_cancelled",
    "subscription_expired", "payment_completed", "addon_payment_completed", "payment_failed",
}
REQUEST_OPS = {
    "inspect", "signup", "select_plan", "start_trial", "confirm_subscription",
    "purchase_addon", "request_plan_change", "cancel",
}


def settlement(c: Contracts, value: Any) -> tuple[str, str, str]:
    value = exact(value, {"priceRef", "currency", "amountMinor", "interval", "authoritative"})
    price, currency = c.ref("priceRef", value["priceRef"]), c.ref("currency", value["currency"])
    if (
        not is_int(value["amountMinor"])
        or not 0 <= value["amountMinor"] <= 1_000_000_000
        or value["authoritative"] is not True
    ):
        raise ContractError("invalid settlement")
    if value["interval"] not in {"month", "year", "one-time"}:
        raise ContractError("invalid settlement interval")
    return price, currency, value["interval"]


def recurring_allowance(c: Contracts, value: Any) -> str:
    value = exact(value, {"metricRef", "includedUnits", "reset", "exhaustion"})
    metric = c.ref("metricRef", value["metricRef"])
    if not is_int(value["includedUnits"]) or not 1 <= value["includedUnits"] <= 1_000_000_000_000:
        raise ContractError("invalid recurring allowance")
    if value["reset"] not in {"month", "year", "billing-interval"}:
        raise ContractError("invalid recurring reset")
    if value["exhaustion"] not in {"block", "prepaid-addon", "metered-overage"}:
        raise ContractError("invalid exhaustion policy")
    return metric


def prepaid_allowance(c: Contracts, value: Any) -> str:
    value = exact(value, {"metricRef", "includedUnits", "reset", "validityDays", "exhaustion"})
    metric = c.ref("metricRef", value["metricRef"])
    if not is_int(value["includedUnits"]) or not 1 <= value["includedUnits"] <= 1_000_000_000_000:
        raise ContractError("invalid prepaid allowance")
    if value["reset"] != "never" or value["exhaustion"] != "block":
        raise ContractError("prepaid allowance must not renew")
    if not is_int(value["validityDays"]) or not 1 <= value["validityDays"] <= 3650:
        raise ContractError("invalid prepaid validity")
    return metric


def _validate_plan_commercial(
    c: Contracts,
    item: dict[str, Any],
    intervals: set[str],
    price_refs: set[str],
    settlement_currencies: set[str],
) -> tuple[str, str | None]:
    model = item["commercial"]
    if not isinstance(model, dict) or "type" not in model:
        raise ContractError("missing commercial model")
    kind, metric = model["type"], None
    if kind == "flat-subscription":
        exact(model, {"type"})
        if not intervals <= {"month", "year"}:
            raise ContractError("subscription settlement must recur")
    elif kind == "usage-subscription":
        model = exact(model, {"type", "usageAllowance"})
        metric = recurring_allowance(c, model["usageAllowance"])
        if not intervals <= {"month", "year"}:
            raise ContractError("usage subscription settlement must recur")
    elif kind == "prepaid-addon":
        model = exact(model, {"type", "usageAllowance", "compatiblePlanRefs"})
        metric = prepaid_allowance(c, model["usageAllowance"])
        compat = unique_str_list(
            model["compatiblePlanRefs"], min_items=1, max_items=32, label="compatiblePlanRefs"
        )
        if intervals != {"one-time"} or len(item["settlements"]) != 1:
            raise ContractError("invalid prepaid commercial model")
        for compatible in compat:
            c.ref("planRef", compatible)
    elif kind == "perpetual-license":
        model = exact(model, {"type"}, {"maintenance"})
        if (
            intervals != {"one-time"}
            or len(item["settlements"]) != 1
            or item["deploymentMode"] not in {"self-hosted", "hybrid"}
        ):
            raise ContractError("invalid perpetual commercial model")
        if "maintenance" in model:
            maint = exact(model["maintenance"], {"settlement", "includedPeriods", "renewal"})
            price, currency, m_interval = settlement(c, maint["settlement"])
            if price in price_refs:
                raise ContractError("duplicate maintenance price")
            price_refs.add(price)
            settlement_currencies.add(currency)
            if (
                m_interval not in {"month", "year"}
                or not is_int(maint["includedPeriods"])
                or not 0 <= maint["includedPeriods"] <= 10
                or maint["renewal"] not in {"optional", "automatic-after-notice"}
            ):
                raise ContractError("invalid maintenance")
    else:
        raise ContractError("unsupported commercial model")
    return kind, metric


def validate_offer(c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    req = {
        "$schema", "schema", "offerId", "version", "plans",
        "localeDefaults", "displayQuotes", "legalPolicyRef",
    }
    value = exact(value, req)
    if value["$schema"] != SCHEMA_URI or value["schema"] != "wellmanifest.saas-offer/v1":
        raise ContractError("unsupported offer")
    c.ref("identifier", value["offerId"])
    if not isinstance(value["version"], str) or SEMVER_RE.fullmatch(value["version"]) is None:
        raise ContractError("invalid offer version")
    policy = value["legalPolicyRef"]
    if not isinstance(policy, str) or len(policy) > 320 or POLICY_REF_RE.fullmatch(policy) is None:
        raise ContractError("invalid legalPolicyRef")
    if not isinstance(value["plans"], list) or not 1 <= len(value["plans"]) <= 32:
        raise ContractError("invalid offer plans")

    plans: dict[str, dict[str, Any]] = {}
    commercial: dict[str, tuple[str, str | None]] = {}
    settlement_currencies: set[str] = set()
    price_refs: set[str] = set()
    parity: dict[str, list[dict[str, Any]]] = {}

    plan_req = {"ref", "name", "settlements", "commercial", "deploymentMode", "entitlements", "public"}
    for raw_item in value["plans"]:
        item = exact(raw_item, plan_req, {"trial", "capabilityParityGroup"})
        ref = c.ref("planRef", item["ref"])
        if ref in plans:
            raise ContractError("duplicate plan")
        if (
            not isinstance(item["name"], str)
            or not item["name"].strip()
            or len(item["name"]) > 120
            or type(item["public"]) is not bool
        ):
            raise ContractError("invalid plan metadata")
        if not isinstance(item["settlements"], list) or not 1 <= len(item["settlements"]) <= 12:
            raise ContractError("plan without settlement option")
        intervals: set[str] = set()
        for option in item["settlements"]:
            price, currency, interval = settlement(c, option)
            if price in price_refs or interval in intervals:
                raise ContractError("duplicate settlement option")
            price_refs.add(price)
            intervals.add(interval)
            settlement_currencies.add(currency)
        plans[ref] = item
        if item["deploymentMode"] not in {"cloud", "self-hosted", "hybrid"}:
            raise ContractError("invalid deployment mode")
        for ent in unique_str_list(item["entitlements"], min_items=1, max_items=64, label="entitlements"):
            c.ref("entitlementRef", ent)
        commercial[ref] = _validate_plan_commercial(
            c, item, intervals, price_refs, settlement_currencies
        )
        if "capabilityParityGroup" in item:
            parity.setdefault(c.ref("identifier", item["capabilityParityGroup"]), []).append(item)

    trial_req = {
        "days", "priceMinor", "requiresPaymentMethod", "conversionPlanRef",
        "conversionMode", "noticeDays", "cancelBeforeCharge",
    }
    for item in value["plans"]:
        if "trial" not in item:
            continue
        trial = exact(item["trial"], trial_req)
        if (
            not is_int(trial["days"])
            or not 1 <= trial["days"] <= 90
            or not is_int(trial["priceMinor"])
            or trial["priceMinor"] != 0
            or type(trial["requiresPaymentMethod"]) is not bool
            or trial["conversionMode"] not in {"explicit-accept", "scheduled-after-notice"}
            or not is_int(trial["noticeDays"])
            or not 1 <= trial["noticeDays"] <= 30
            or trial["noticeDays"] >= trial["days"]
            or trial["cancelBeforeCharge"] is not True
        ):
            raise ContractError("unsafe trial")
        if c.ref("planRef", trial["conversionPlanRef"]) not in plans or (
            trial["conversionPlanRef"] == item["ref"]
        ):
            raise ContractError("invalid trial conversion")
        if (
            trial["conversionMode"] == "scheduled-after-notice"
            and trial["requiresPaymentMethod"] is not True
        ):
            raise ContractError("scheduled charge lacks payment method policy")

    for ref, item in plans.items():
        kind, metric = commercial[ref]
        if kind != "prepaid-addon":
            continue
        for compatible in item["commercial"]["compatiblePlanRefs"]:
            if compatible not in commercial or commercial[compatible][0] != "usage-subscription":
                raise ContractError("prepaid add-on targets non-usage plan")
            if commercial[compatible][1] != metric:
                raise ContractError("prepaid add-on metric mismatch")

    for items in parity.values():
        if len(items) < 2:
            raise ContractError("capability parity group needs peers")
        expected = (
            tuple(sorted(items[0]["entitlements"])),
            items[0]["deploymentMode"],
            items[0]["commercial"]["type"],
        )
        if any(
            (tuple(sorted(i["entitlements"])), i["deploymentMode"], i["commercial"]["type"]) != expected
            for i in items[1:]
        ):
            raise ContractError("capability parity mismatch")

    if not isinstance(value["localeDefaults"], list) or not 1 <= len(value["localeDefaults"]) <= 64:
        raise ContractError("invalid locale defaults")
    locales: set[str] = set()
    display_currencies: set[str] = set()
    for default in value["localeDefaults"]:
        default = exact(default, {"locale", "currency"})
        if (
            not isinstance(default["locale"], str)
            or LOCALE_RE.fullmatch(default["locale"]) is None
            or default["locale"] in locales
        ):
            raise ContractError("invalid locale default")
        locales.add(default["locale"])
        display_currencies.add(c.ref("currency", default["currency"]))

    if not isinstance(value["displayQuotes"], list) or len(value["displayQuotes"]) > 1024:
        raise ContractError("invalid display quotes")
    pairs: set[tuple[str, str]] = set()
    quote_req = {"baseCurrency", "quoteCurrency", "rateNumerator", "rateDenominator", "asOf", "indicative"}
    for quote in value["displayQuotes"]:
        quote = exact(quote, quote_req)
        base, target = c.ref("currency", quote["baseCurrency"]), c.ref("currency", quote["quoteCurrency"])
        pair = (base, target)
        if (
            base == target
            or pair in pairs
            or quote["indicative"] is not True
            or not is_int(quote["rateNumerator"])
            or not 1 <= quote["rateNumerator"] <= 1_000_000_000
            or not is_int(quote["rateDenominator"])
            or not 1 <= quote["rateDenominator"] <= 1_000_000_000
        ):
            raise ContractError("invalid display quote")
        pairs.add(pair)
        if not isinstance(quote["asOf"], str) or len(quote["asOf"]) != 10:
            raise ContractError("invalid quote date")
        try:
            date.fromisoformat(quote["asOf"])
        except ValueError as error:
            raise ContractError("invalid quote date") from error

    for base in settlement_currencies:
        for target in display_currencies:
            if base != target and (base, target) not in pairs:
                raise ContractError("display conversion coverage missing")


def validate_request(c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    req = {
        "$schema", "schema", "requestId", "operation", "accountRef", "tenantRef",
        "planRef", "priceRef", "billingRef", "intentRef", "grantRef", "planHash",
    }
    value = exact(value, req)
    if value["$schema"] != SCHEMA_URI or value["schema"] != "wellmanifest.saas-lifecycle-request/v1":
        raise ContractError("unsupported request")
    c.ref("identifier", value["requestId"])
    if value["operation"] not in REQUEST_OPS:
        raise ContractError("unsupported operation")
    refs = ("accountRef", "tenantRef", "planRef", "priceRef", "billingRef", "intentRef", "grantRef")
    for name in refs:
        c.ref(name, value[name])
    c.ref("sha256", value["planHash"])


def _validate_lifecycle_subblocks(c: Contracts, value: dict[str, Any]) -> None:
    if "trial" in value:
        trial_req = {
            "startedAt", "endsAt", "conversionPlanRef", "conversionMode",
            "noticeAt", "paymentMethodPresent", "cancelledAt",
        }
        trial = exact(value["trial"], trial_req)
        start, end, notice = (
            time_value(trial["startedAt"]),
            time_value(trial["endsAt"]),
            time_value(trial["noticeAt"]),
        )
        if not start < notice < end:
            raise ContractError("invalid trial chronology")
        c.ref("planRef", trial["conversionPlanRef"])
        if trial["conversionMode"] not in {"explicit-accept", "scheduled-after-notice"}:
            raise ContractError("invalid trial conversionMode")
        if type(trial["paymentMethodPresent"]) is not bool:
            raise ContractError("invalid trial paymentMethodPresent")
        if trial["cancelledAt"] is not None:
            time_value(trial["cancelledAt"])
        if (
            trial["conversionMode"] == "scheduled-after-notice"
            and trial["paymentMethodPresent"] is not True
        ):
            raise ContractError("scheduled conversion not eligible")

    if "subscription" in value:
        sub_req = {
            "providerRef", "billingRef", "providerPlanRef", "status",
            "verificationMode", "verifiedAt", "settlement",
        }
        sub = exact(value["subscription"], sub_req)
        c.ref("providerRef", sub["providerRef"])
        c.ref("billingRef", sub["billingRef"])
        c.ref("billingRef", sub["providerPlanRef"])
        if sub["status"] not in {"pending", "active", "suspended", "cancelled", "expired"}:
            raise ContractError("invalid subscription status")
        time_value(sub["verifiedAt"])
        settlement(c, sub["settlement"])
        if sub["verificationMode"] != "server-side":
            raise ContractError("client-trusted subscription")
        if value["state"] == "active" and sub["status"] != "active":
            raise ContractError("active account has inactive subscription")

    if "provisioning" in value:
        prov_req = {"outboxRef", "idempotencyKey", "deploymentRef", "state", "attempts", "updatedAt"}
        p = exact(value["provisioning"], prov_req, {"externalRef", "errorEvidenceRef"})
        c.ref("outboxRef", p["outboxRef"])
        c.ref("identifier", p["idempotencyKey"])
        c.ref("deploymentRef", p["deploymentRef"])
        if p["state"] not in {"pending", "running", "completed", "failed"}:
            raise ContractError("invalid provisioning state")
        time_value(p["updatedAt"])
        if not is_int(p["attempts"]) or not 0 <= p["attempts"] <= 20:
            raise ContractError("provision attempts out of range")
        if "externalRef" in p:
            ext = p["externalRef"]
            if not isinstance(ext, str) or len(ext) > 320 or RESOURCE_REF_RE.fullmatch(ext) is None:
                raise ContractError("invalid externalRef")
        if "errorEvidenceRef" in p:
            c.ref("evidenceRef", p["errorEvidenceRef"])
        if p["state"] == "completed" and "externalRef" not in p:
            raise ContractError("completed provisioning lacks resource")
        if p["state"] == "failed" and "errorEvidenceRef" not in p:
            raise ContractError("failed provisioning lacks evidence")
        if value["state"] == "active" and p["state"] != "completed":
            raise ContractError("active account not provisioned")


def validate_lifecycle(c: Contracts, value: Any) -> None:
    reject_sensitive(value)
    req = {
        "$schema", "schema", "accountRef", "tenantRef", "currentPlanRef",
        "state", "version", "updatedAt", "events", "usageGrants",
    }
    value = exact(value, req, {"trial", "subscription", "provisioning"})
    if value["$schema"] != SCHEMA_URI or value["schema"] != "wellmanifest.saas-lifecycle-state/v1":
        raise ContractError("unsupported state")
    c.ref("accountRef", value["accountRef"])
    c.ref("tenantRef", value["tenantRef"])
    c.ref("planRef", value["currentPlanRef"])
    if value["state"] not in LIFECYCLE_STATES:
        raise ContractError("invalid lifecycle state")
    if not is_int(value["version"]) or value["version"] < 1:
        raise ContractError("invalid lifecycle version")
    time_value(value["updatedAt"])
    if not isinstance(value["events"], list) or len(value["events"]) > 10_000:
        raise ContractError("invalid billing events")
    if not isinstance(value["usageGrants"], list) or len(value["usageGrants"]) > 10_000:
        raise ContractError("invalid usage grants")

    if value["state"] in {"trial_active", "trial_expiring"} and "trial" not in value:
        raise ContractError("trial state missing")
    if (
        value["state"] in {"paid_pending_provisioning", "active", "plan_change_pending", "suspended"}
        and "subscription" not in value
    ):
        raise ContractError("subscription missing")
    if (
        value["state"] in {"paid_pending_provisioning", "active", "plan_change_pending"}
        and "provisioning" not in value
    ):
        raise ContractError("provisioning missing")
    _validate_lifecycle_subblocks(c, value)

    seen_event: set[str] = set()
    seen_key: set[str] = set()
    ev_req = {
        "eventRef", "type", "digest", "idempotencyKey", "signatureVerified", "verifiedAt", "processedAt"
    }
    for event in value["events"]:
        event = exact(event, ev_req)
        ref, key = c.ref("eventRef", event["eventRef"]), c.ref("identifier", event["idempotencyKey"])
        if event["type"] not in BILLING_EVENT_TYPES:
            raise ContractError("invalid billing event type")
        if ref in seen_event or key in seen_key:
            raise ContractError("duplicate billing event")
        seen_event.add(ref)
        seen_key.add(key)
        c.ref("sha256Ref", event["digest"])
        if event["signatureVerified"] is not True or time_value(event["processedAt"]) < time_value(
            event["verifiedAt"]
        ):
            raise ContractError("unverified event")

    seen_grants: set[tuple[str, str, str, str]] = set()
    gr_req = {
        "sourcePlanRef", "priceRef", "metricRef", "unitsGranted", "unitsRemaining",
        "validFrom", "expiresAt", "billingRef", "verificationMode", "verifiedAt",
    }
    for grant in value["usageGrants"]:
        grant = exact(grant, gr_req)
        identity = (
            c.ref("planRef", grant["sourcePlanRef"]),
            c.ref("priceRef", grant["priceRef"]),
            c.ref("metricRef", grant["metricRef"]),
            c.ref("billingRef", grant["billingRef"]),
        )
        if identity in seen_grants:
            raise ContractError("duplicate usage grant")
        seen_grants.add(identity)
        if (
            not is_int(grant["unitsGranted"])
            or not is_int(grant["unitsRemaining"])
            or not 1 <= grant["unitsGranted"] <= 1_000_000_000_000
            or not 0 <= grant["unitsRemaining"] <= grant["unitsGranted"]
        ):
            raise ContractError("invalid usage grant units")
        verified, valid, expires = (
            time_value(grant["verifiedAt"]),
            time_value(grant["validFrom"]),
            time_value(grant["expiresAt"]),
        )
        if grant["verificationMode"] != "server-side" or not verified <= valid < expires:
            raise ContractError("unverified usage grant")


