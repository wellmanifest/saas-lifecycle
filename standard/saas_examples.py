"""Canonical valid contract examples for SaaS lifecycle v1 conformance."""

from __future__ import annotations

import copy
from typing import Any

from saas_contracts import SCHEMA_URI


def offer_example() -> dict[str, Any]:
    basic = "plan://example.test/basic/v1"
    pro = "plan://example.test/pro/v1"
    prepaid = "plan://example.test/prepaid-actions/v1"
    action = "metric://example.test/actions/office/v1"
    common = ["entitlement://example.test/subactor/platform/v1"]
    return {
        "$schema": SCHEMA_URI,
        "schema": "wellmanifest.saas-offer/v1",
        "offerId": "offer-2026-08",
        "version": "1.0.0",
        "plans": [
            {
                "ref": "plan://example.test/trial/v1",
                "name": "30 day trial",
                "settlements": [
                    {
                        "priceRef": "price://example.test/trial/month/v1",
                        "currency": "PLN",
                        "amountMinor": 0,
                        "interval": "month",
                        "authoritative": True,
                    }
                ],
                "commercial": {"type": "flat-subscription"},
                "deploymentMode": "cloud",
                "entitlements": common,
                "trial": {
                    "days": 30,
                    "priceMinor": 0,
                    "requiresPaymentMethod": False,
                    "conversionPlanRef": basic,
                    "conversionMode": "explicit-accept",
                    "noticeDays": 7,
                    "cancelBeforeCharge": True,
                },
                "public": True,
            },
            {
                "ref": basic,
                "name": "Basic",
                "settlements": [
                    {
                        "priceRef": "price://example.test/basic/month/v1",
                        "currency": "PLN",
                        "amountMinor": 1000,
                        "interval": "month",
                        "authoritative": True,
                    },
                    {
                        "priceRef": "price://example.test/basic/year/v1",
                        "currency": "PLN",
                        "amountMinor": 10000,
                        "interval": "year",
                        "authoritative": True,
                    },
                ],
                "commercial": {
                    "type": "usage-subscription",
                    "usageAllowance": {
                        "metricRef": action,
                        "includedUnits": 1000,
                        "reset": "month",
                        "exhaustion": "prepaid-addon",
                    },
                },
                "deploymentMode": "cloud",
                "capabilityParityGroup": "cloud-actions",
                "entitlements": common,
                "public": True,
            },
            {
                "ref": pro,
                "name": "Pro",
                "settlements": [
                    {
                        "priceRef": "price://example.test/pro/month/v1",
                        "currency": "PLN",
                        "amountMinor": 10000,
                        "interval": "month",
                        "authoritative": True,
                    },
                    {
                        "priceRef": "price://example.test/pro/year/v1",
                        "currency": "PLN",
                        "amountMinor": 100000,
                        "interval": "year",
                        "authoritative": True,
                    },
                ],
                "commercial": {
                    "type": "usage-subscription",
                    "usageAllowance": {
                        "metricRef": action,
                        "includedUnits": 10000,
                        "reset": "month",
                        "exhaustion": "prepaid-addon",
                    },
                },
                "deploymentMode": "cloud",
                "capabilityParityGroup": "cloud-actions",
                "entitlements": common,
                "public": True,
            },
            {
                "ref": prepaid,
                "name": "PrePaid",
                "settlements": [
                    {
                        "priceRef": "price://example.test/prepaid-actions/once/v1",
                        "currency": "PLN",
                        "amountMinor": 10000,
                        "interval": "one-time",
                        "authoritative": True,
                    }
                ],
                "commercial": {
                    "type": "prepaid-addon",
                    "usageAllowance": {
                        "metricRef": action,
                        "includedUnits": 10000,
                        "reset": "never",
                        "validityDays": 365,
                        "exhaustion": "block",
                    },
                    "compatiblePlanRefs": [basic, pro],
                },
                "deploymentMode": "cloud",
                "entitlements": ["entitlement://example.test/subactor/action-topup/v1"],
                "public": True,
            },
            {
                "ref": "plan://example.test/on-premise/v1",
                "name": "On-Premise",
                "settlements": [
                    {
                        "priceRef": "price://example.test/on-premise/license/v1",
                        "currency": "EUR",
                        "amountMinor": 290000,
                        "interval": "one-time",
                        "authoritative": True,
                    }
                ],
                "commercial": {
                    "type": "perpetual-license",
                    "maintenance": {
                        "settlement": {
                            "priceRef": "price://example.test/on-premise/maintenance-year/v1",
                            "currency": "EUR",
                            "amountMinor": 49000,
                            "interval": "year",
                            "authoritative": True,
                        },
                        "includedPeriods": 1,
                        "renewal": "optional",
                    },
                },
                "deploymentMode": "self-hosted",
                "entitlements": ["entitlement://example.test/subactor/self-hosted/v1"],
                "public": True,
            },
        ],
        "localeDefaults": [
            {"locale": "pl", "currency": "PLN"},
            {"locale": "en", "currency": "EUR"},
            {"locale": "de", "currency": "EUR"},
        ],
        "displayQuotes": [
            {
                "baseCurrency": "PLN",
                "quoteCurrency": "EUR",
                "rateNumerator": 100,
                "rateDenominator": 428,
                "asOf": "2026-08-12",
                "indicative": True,
            },
            {
                "baseCurrency": "EUR",
                "quoteCurrency": "PLN",
                "rateNumerator": 428,
                "rateDenominator": 100,
                "asOf": "2026-08-12",
                "indicative": True,
            },
        ],
        "legalPolicyRef": "policy://example.test/saas/terms/v1",
    }


def request_example() -> dict[str, Any]:
    return {
        "$schema": SCHEMA_URI,
        "schema": "wellmanifest.saas-lifecycle-request/v1",
        "requestId": "request-001",
        "operation": "purchase_addon",
        "accountRef": "account://example.test/account-001",
        "tenantRef": "tenant://example.test/acme",
        "planRef": "plan://example.test/prepaid-actions/v1",
        "priceRef": "price://example.test/prepaid-actions/once/v1",
        "billingRef": "billing://example.test/transactions/topup-001",
        "intentRef": "intent://example.test/addons/request-001",
        "grantRef": "grant://example.test/addons/request-001/g1",
        "planHash": "a" * 64,
    }


def lifecycle_example() -> dict[str, Any]:
    return {
        "$schema": SCHEMA_URI,
        "schema": "wellmanifest.saas-lifecycle-state/v1",
        "accountRef": "account://example.test/account-001",
        "tenantRef": "tenant://example.test/acme",
        "currentPlanRef": "plan://example.test/basic/v1",
        "state": "active",
        "version": 7,
        "updatedAt": "2026-08-12T12:00:00Z",
        "subscription": {
            "providerRef": "provider://example.test/paypal",
            "billingRef": "billing://example.test/subscriptions/sub-001",
            "providerPlanRef": "billing://example.test/plans/basic",
            "status": "active",
            "verificationMode": "server-side",
            "verifiedAt": "2026-08-12T11:58:00Z",
            "settlement": {
                "priceRef": "price://example.test/basic/month/v1",
                "currency": "PLN",
                "amountMinor": 1000,
                "interval": "month",
                "authoritative": True,
            },
        },
        "provisioning": {
            "outboxRef": "outbox://example.test/provisioning/item-001",
            "idempotencyKey": "account-001-basic-v1",
            "deploymentRef": "deployment://example.test/tenant/acme/v1",
            "state": "completed",
            "attempts": 1,
            "updatedAt": "2026-08-12T12:00:00Z",
            "externalRef": "resource://example.test/tenants/acme",
        },
        "events": [
            {
                "eventRef": "event://example.test/paypal/event-001",
                "type": "addon_payment_completed",
                "digest": "sha256:" + "b" * 64,
                "idempotencyKey": "event-001",
                "signatureVerified": True,
                "verifiedAt": "2026-08-12T11:57:00Z",
                "processedAt": "2026-08-12T11:58:00Z",
            }
        ],
        "usageGrants": [
            {
                "sourcePlanRef": "plan://example.test/prepaid-actions/v1",
                "priceRef": "price://example.test/prepaid-actions/once/v1",
                "metricRef": "metric://example.test/actions/office/v1",
                "unitsGranted": 10000,
                "unitsRemaining": 10000,
                "validFrom": "2026-08-12T11:58:00Z",
                "expiresAt": "2027-08-12T11:58:00Z",
                "billingRef": "billing://example.test/transactions/topup-001",
                "verificationMode": "server-side",
                "verifiedAt": "2026-08-12T11:58:00Z",
            }
        ],
    }


def receipt_example() -> dict[str, Any]:
    return {
        "$schema": SCHEMA_URI,
        "schema": "wellmanifest.saas-lifecycle-receipt/v1",
        "requestId": "request-001",
        "accountRef": "account://example.test/account-001",
        "tenantRef": "tenant://example.test/acme",
        "planRef": "plan://example.test/prepaid-actions/v1",
        "priceRef": "price://example.test/prepaid-actions/once/v1",
        "inputHash": "c" * 64,
        "planHash": "a" * 64,
        "outcome": "addon_activated",
        "startedAt": "2026-08-12T11:50:00Z",
        "completedAt": "2026-08-12T12:00:00Z",
        "evidenceRefs": ["evidence://example.test/saas/addon-001/r1"],
        "secretsRedacted": True,
        "paymentDataStored": False,
    }


def usage_entry_example() -> dict[str, Any]:
    return {
        "$schema": SCHEMA_URI,
        "schema": "wellmanifest.saas-usage-ledger-entry/v1",
        "entryRef": "usage://example.test/entries/attempt-001/reserve",
        "idempotencyKey": "attempt-001-reserve",
        "kind": "reserve",
        "accountRef": "account://example.test/account-001",
        "tenantRef": "tenant://example.test/acme",
        "sourcePlanRef": "plan://example.test/basic/v1",
        "priceRef": "price://example.test/basic/month/v1",
        "usageGrantRef": "grant://example.test/usage/basic-2026-08",
        "metricRef": "metric://example.test/uri-operations/v1",
        "meteringRuleRef": "metering-rule://example.test/subactor-cloud/v1",
        "attribution": {
            "organizationRef": "organization://example.test/acme",
            "projectRef": "project://example.test/customer-portal",
            "ticketRef": "ticket://example.test/PLF-123",
            "principalRef": "authority://principal/subactor-coding-agent",
            "processRunRef": "process-run://example.test/run-001",
            "attemptRef": "attempt://example.test/run-001/step-01",
            "uriProcessRef": "deployment://example.test/site/command/publish",
            "operationClassRef": "operation-class://example.test/uri-process/write/v1",
        },
        "authority": {
            "decisionRef": "evidence://example.test/authority/decision-001/r1",
            "authorityGrantRef": "authority://grant/subactor/deploy-001",
            "leaseRef": None,
            "delegationDigest": None,
        },
        "measurement": {
            "kind": "estimate",
            "observedUnits": 1,
            "billableUnits": 1,
            "calculationDigest": "sha256:" + "d" * 64,
        },
        "ledgerUnits": 1,
        "operationOutcome": "pending",
        "recordedAt": "2026-08-12T12:01:00Z",
        "evidenceRefs": ["evidence://example.test/usage/attempt-001/r1"],
        "secretsRedacted": True,
        "paymentDataStored": False,
    }


def usage_ledger_example() -> list[dict[str, Any]]:
    reserve = usage_entry_example()
    reserve["measurement"]["observedUnits"] = 3
    reserve["measurement"]["billableUnits"] = 3
    reserve["ledgerUnits"] = 3

    def derived(kind: str, units: int, related: str) -> dict[str, Any]:
        val = copy.deepcopy(reserve)
        val["kind"] = kind
        val["entryRef"] = f"usage://example.test/entries/attempt-001/{kind}"
        val["idempotencyKey"] = f"attempt-001-{kind}"
        val["relatedEntryRef"] = related
        val["operationOutcome"] = "succeeded"
        val["ledgerUnits"] = units
        if kind == "settle":
            val["measurement"].update({"kind": "actual", "observedUnits": 2, "billableUnits": 2})
        else:
            val["measurement"].update(
                {"kind": "not-applicable", "observedUnits": 0, "billableUnits": 0}
            )
        return val

    settle = derived("settle", 2, reserve["entryRef"])
    release = derived("release", 1, reserve["entryRef"])
    refund = derived("refund", 1, settle["entryRef"])
    waive = copy.deepcopy(reserve)
    waive.update(
        {
            "entryRef": "usage://example.test/entries/attempt-002/waive",
            "idempotencyKey": "attempt-002-waive",
            "kind": "waive",
            "ledgerUnits": 0,
            "operationOutcome": "denied",
        }
    )
    waive["attribution"]["attemptRef"] = "attempt://example.test/run-001/step-02"
    waive["measurement"].update({"kind": "actual", "observedUnits": 1, "billableUnits": 1})
    return [reserve, settle, release, refund, waive]
