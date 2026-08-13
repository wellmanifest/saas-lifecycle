#!/usr/bin/env python3
"""Dependency-free conformance checks for SaaS lifecycle v1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "saas-lifecycle.schema.json"
GRAMMAR_PATH = ROOT / "saas-lifecycle.v1.gbnf"
PROFILE_SCHEMA_PATH = ROOT / "saas-adapter-profile.schema.json"
PROFILE_EXAMPLES_PATH = ROOT / "adapter-profiles.examples.json"
SCHEMA_DIGEST = "659e2d0124b236e86f76786c37bc22bbd326f274eb6b9ca9c3a20d82e33f26cd"
GRAMMAR_DIGEST = "2565b1c0e93c1f5ee84c299428ef8592e295b4a3337585409ae1ee19644d7690"
PROFILE_SCHEMA_DIGEST = "060495e3dda6a80bc67d861d55422dff65df912028b0d3a7a598959de3df7054"
PROFILE_EXAMPLES_DIGEST = "5ed1f16934de26008feafdcdd98577298db2474c8ddf8b5aa0128aadfb52fc49"
SCHEMA_URI = "https://wellmanifest.dev/schemas/saas-lifecycle/v1"
PROFILE_SCHEMA_URI = "https://wellmanifest.dev/schemas/saas-adapter-profile/v1"
SENSITIVE = re.compile(r"(?:password|passwd|token|secret|cookie|api[-_]?key|card|cvv|private[-_]?key|webhook[-_]?signature)", re.I)
SAFE_ASSERTIONS = {"secretsRedacted", "paymentDataStored", "signatureVerified"}
UNSAFE_POINTER_SEGMENT = re.compile(r"(?:password|passwd|token|secret|cookie|api[-_]?key|card|cvv|private[-_]?key|webhook[-_]?signature|host(?:name)?|user(?:name)?|docroot|domain|source[-_]?dir|vault[-_]?url|base[-_]?url)", re.I)


class ContractError(ValueError):
    """A bounded error that never repeats untrusted provider data."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def exact(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict): raise ContractError("expected object")
    optional = optional or set()
    if set(value) - required - optional: raise ContractError("undeclared field")
    if required - set(value): raise ContractError("missing field")
    return value


def time_value(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 40: raise ContractError("invalid date-time")
    try: result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error: raise ContractError("invalid date-time") from error
    if result.tzinfo is None: raise ContractError("timezone required")
    return result


def reject_sensitive(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SENSITIVE.search(key) and key not in SAFE_ASSERTIONS: raise ContractError("sensitive data channel")
            reject_sensitive(child)
    elif isinstance(value, list):
        for child in value: reject_sensitive(child)


class Contracts:
    def __init__(self) -> None:
        self.schema=json.loads(SCHEMA_PATH.read_text("utf-8")); self.grammar=GRAMMAR_PATH.read_text("utf-8")
        self.profile_schema=json.loads(PROFILE_SCHEMA_PATH.read_text("utf-8")); self.profile_examples=json.loads(PROFILE_EXAMPLES_PATH.read_text("utf-8"))
        defs=self.schema.get("$defs", {})
        names=("identifier","sha256","sha256Ref","accountRef","tenantRef","planRef","priceRef","providerRef","billingRef","intentRef","grantRef","eventRef","evidenceRef","outboxRef","deploymentRef","entitlementRef","metricRef","currency")
        self.patterns={name:re.compile(defs[name]["pattern"]) for name in names}

    def ref(self,name:str,value:Any)->str:
        if not isinstance(value,str) or self.patterns[name].fullmatch(value) is None: raise ContractError(f"invalid {name}")
        return value

    def integrity(self)->None:
        if self.schema.get("$schema")!="https://json-schema.org/draft/2020-12/schema" or self.schema.get("$id")!=SCHEMA_URI: raise ContractError("schema identity mismatch")
        if digest(canonical(self.schema))!=SCHEMA_DIGEST or digest(self.grammar)!=GRAMMAR_DIGEST: raise ContractError("contract digest mismatch")
        if self.profile_schema.get("$schema")!="https://json-schema.org/draft/2020-12/schema" or self.profile_schema.get("$id")!=PROFILE_SCHEMA_URI: raise ContractError("profile schema identity mismatch")
        if digest(canonical(self.profile_schema))!=PROFILE_SCHEMA_DIGEST or digest(canonical(self.profile_examples))!=PROFILE_EXAMPLES_DIGEST: raise ContractError("profile contract digest mismatch")
        if {x.get("$ref") for x in self.schema.get("oneOf",[])}!={"#/$defs/offer","#/$defs/request","#/$defs/lifecycle","#/$defs/receipt"}: raise ContractError("document variants incomplete")
        if {x.get("$ref") for x in self.profile_schema.get("oneOf",[])}!={"#/$defs/paymentProfile","#/$defs/deploymentProfile"}: raise ContractError("profile variants incomplete")
        if self.profile_examples.get("schema")!="wellmanifest.saas-adapter-profile-examples/v1": raise ContractError("profile examples identity mismatch")
        for fragment in ("root ::= request","payment status","purchase_addon","plan-ref ::=","price-ref ::=","billing-ref ::=","sha256 ::="):
            if fragment not in self.grammar: raise ContractError("grammar incomplete")
        self._closed(self.schema); self._closed(self.profile_schema)

    def _closed(self,value:Any)->None:
        if isinstance(value,dict):
            if value.get("type")=="object" and value.get("additionalProperties") is not False: raise ContractError("open object schema")
            for child in value.values(): self._closed(child)
        elif isinstance(value,list):
            for child in value: self._closed(child)


def offer_example()->dict[str,Any]:
    basic="plan://example.test/basic/v1"; pro="plan://example.test/pro/v1"
    prepaid="plan://example.test/prepaid-actions/v1"; action="metric://example.test/actions/office/v1"
    common=["entitlement://example.test/subactor/platform/v1"]
    return {
        "$schema":SCHEMA_URI,"schema":"wellmanifest.saas-offer/v1","offerId":"offer-2026-08","version":"1.0.0",
        "plans":[
            {"ref":"plan://example.test/trial/v1","name":"30 day trial","settlements":[{"priceRef":"price://example.test/trial/month/v1","currency":"PLN","amountMinor":0,"interval":"month","authoritative":True}],"commercial":{"type":"flat-subscription"},"deploymentMode":"cloud","entitlements":common,"trial":{"days":30,"priceMinor":0,"requiresPaymentMethod":False,"conversionPlanRef":basic,"conversionMode":"explicit-accept","noticeDays":7,"cancelBeforeCharge":True},"public":True},
            {"ref":basic,"name":"Basic","settlements":[{"priceRef":"price://example.test/basic/month/v1","currency":"PLN","amountMinor":1000,"interval":"month","authoritative":True},{"priceRef":"price://example.test/basic/year/v1","currency":"PLN","amountMinor":10000,"interval":"year","authoritative":True}],"commercial":{"type":"usage-subscription","usageAllowance":{"metricRef":action,"includedUnits":1000,"reset":"month","exhaustion":"prepaid-addon"}},"deploymentMode":"cloud","capabilityParityGroup":"cloud-actions","entitlements":common,"public":True},
            {"ref":pro,"name":"Pro","settlements":[{"priceRef":"price://example.test/pro/month/v1","currency":"PLN","amountMinor":10000,"interval":"month","authoritative":True},{"priceRef":"price://example.test/pro/year/v1","currency":"PLN","amountMinor":100000,"interval":"year","authoritative":True}],"commercial":{"type":"usage-subscription","usageAllowance":{"metricRef":action,"includedUnits":10000,"reset":"month","exhaustion":"prepaid-addon"}},"deploymentMode":"cloud","capabilityParityGroup":"cloud-actions","entitlements":common,"public":True},
            {"ref":prepaid,"name":"PrePaid","settlements":[{"priceRef":"price://example.test/prepaid-actions/once/v1","currency":"PLN","amountMinor":10000,"interval":"one-time","authoritative":True}],"commercial":{"type":"prepaid-addon","usageAllowance":{"metricRef":action,"includedUnits":10000,"reset":"never","validityDays":365,"exhaustion":"block"},"compatiblePlanRefs":[basic,pro]},"deploymentMode":"cloud","entitlements":["entitlement://example.test/subactor/action-topup/v1"],"public":True},
            {"ref":"plan://example.test/on-premise/v1","name":"On-Premise","settlements":[{"priceRef":"price://example.test/on-premise/license/v1","currency":"EUR","amountMinor":290000,"interval":"one-time","authoritative":True}],"commercial":{"type":"perpetual-license","maintenance":{"settlement":{"priceRef":"price://example.test/on-premise/maintenance-year/v1","currency":"EUR","amountMinor":49000,"interval":"year","authoritative":True},"includedPeriods":1,"renewal":"optional"}},"deploymentMode":"self-hosted","entitlements":["entitlement://example.test/subactor/self-hosted/v1"],"public":True},
        ],
        "localeDefaults":[{"locale":"pl","currency":"PLN"},{"locale":"en","currency":"EUR"},{"locale":"de","currency":"EUR"}],
        "displayQuotes":[
            {"baseCurrency":"PLN","quoteCurrency":"EUR","rateNumerator":100,"rateDenominator":428,"asOf":"2026-08-12","indicative":True},
            {"baseCurrency":"EUR","quoteCurrency":"PLN","rateNumerator":428,"rateDenominator":100,"asOf":"2026-08-12","indicative":True},
        ],
        "legalPolicyRef":"policy://example.test/saas/terms/v1",
    }


def request_example()->dict[str,Any]:
    return {"$schema":SCHEMA_URI,"schema":"wellmanifest.saas-lifecycle-request/v1","requestId":"request-001","operation":"purchase_addon","accountRef":"account://example.test/account-001","tenantRef":"tenant://example.test/acme","planRef":"plan://example.test/prepaid-actions/v1","priceRef":"price://example.test/prepaid-actions/once/v1","billingRef":"billing://example.test/transactions/topup-001","intentRef":"intent://example.test/addons/request-001","grantRef":"grant://example.test/addons/request-001/g1","planHash":"a"*64}


def lifecycle_example()->dict[str,Any]:
    return {
        "$schema":SCHEMA_URI,"schema":"wellmanifest.saas-lifecycle-state/v1","accountRef":"account://example.test/account-001","tenantRef":"tenant://example.test/acme","currentPlanRef":"plan://example.test/basic/v1","state":"active","version":7,"updatedAt":"2026-08-12T12:00:00Z",
        "subscription":{"providerRef":"provider://example.test/paypal","billingRef":"billing://example.test/subscriptions/sub-001","providerPlanRef":"billing://example.test/plans/basic","status":"active","verificationMode":"server-side","verifiedAt":"2026-08-12T11:58:00Z","settlement":{"priceRef":"price://example.test/basic/month/v1","currency":"PLN","amountMinor":1000,"interval":"month","authoritative":True}},
        "provisioning":{"outboxRef":"outbox://example.test/provisioning/item-001","idempotencyKey":"account-001-basic-v1","deploymentRef":"deployment://example.test/tenant/acme/v1","state":"completed","attempts":1,"updatedAt":"2026-08-12T12:00:00Z","externalRef":"resource://example.test/tenants/acme"},
        "events":[{"eventRef":"event://example.test/paypal/event-001","type":"addon_payment_completed","digest":"sha256:"+"b"*64,"idempotencyKey":"event-001","signatureVerified":True,"verifiedAt":"2026-08-12T11:57:00Z","processedAt":"2026-08-12T11:58:00Z"}],
        "usageGrants":[{"sourcePlanRef":"plan://example.test/prepaid-actions/v1","priceRef":"price://example.test/prepaid-actions/once/v1","metricRef":"metric://example.test/actions/office/v1","unitsGranted":10000,"unitsRemaining":10000,"validFrom":"2026-08-12T11:58:00Z","expiresAt":"2027-08-12T11:58:00Z","billingRef":"billing://example.test/transactions/topup-001","verificationMode":"server-side","verifiedAt":"2026-08-12T11:58:00Z"}],
    }


def receipt_example()->dict[str,Any]:
    return {"$schema":SCHEMA_URI,"schema":"wellmanifest.saas-lifecycle-receipt/v1","requestId":"request-001","accountRef":"account://example.test/account-001","tenantRef":"tenant://example.test/acme","planRef":"plan://example.test/prepaid-actions/v1","priceRef":"price://example.test/prepaid-actions/once/v1","inputHash":"c"*64,"planHash":"a"*64,"outcome":"addon_activated","startedAt":"2026-08-12T11:50:00Z","completedAt":"2026-08-12T12:00:00Z","evidenceRefs":["evidence://example.test/saas/addon-001/r1"],"secretsRedacted":True,"paymentDataStored":False}


def settlement(c:Contracts,value:Any)->tuple[str,str,str]:
    value=exact(value,{"priceRef","currency","amountMinor","interval","authoritative"})
    price=c.ref("priceRef",value["priceRef"]); currency=c.ref("currency",value["currency"])
    if type(value["amountMinor"]) is not int or not 0<=value["amountMinor"]<=1_000_000_000 or value["authoritative"] is not True: raise ContractError("invalid settlement")
    if value["interval"] not in {"month","year","one-time"}: raise ContractError("invalid settlement interval")
    return price,currency,value["interval"]


def recurring_allowance(c:Contracts,value:Any)->str:
    value=exact(value,{"metricRef","includedUnits","reset","exhaustion"})
    metric=c.ref("metricRef",value["metricRef"])
    if not isinstance(value["includedUnits"],int) or not 1<=value["includedUnits"]<=1_000_000_000_000: raise ContractError("invalid recurring allowance")
    if value["reset"] not in {"month","year","billing-interval"}: raise ContractError("invalid recurring reset")
    if value["exhaustion"] not in {"block","prepaid-addon","metered-overage"}: raise ContractError("invalid exhaustion policy")
    return metric


def prepaid_allowance(c:Contracts,value:Any)->str:
    value=exact(value,{"metricRef","includedUnits","reset","validityDays","exhaustion"})
    metric=c.ref("metricRef",value["metricRef"])
    if not isinstance(value["includedUnits"],int) or not 1<=value["includedUnits"]<=1_000_000_000_000: raise ContractError("invalid prepaid allowance")
    if value["reset"]!="never" or value["exhaustion"]!="block": raise ContractError("prepaid allowance must not renew")
    if not isinstance(value["validityDays"],int) or not 1<=value["validityDays"]<=3650: raise ContractError("invalid prepaid validity")
    return metric


def validate_offer(c:Contracts,value:Any)->None:
    value=exact(value,{"$schema","schema","offerId","version","plans","localeDefaults","displayQuotes","legalPolicyRef"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-offer/v1": raise ContractError("unsupported offer")
    c.ref("identifier",value["offerId"])
    plans:dict[str,dict[str,Any]]={}; commercial:dict[str,tuple[str,str|None]]={}; settlement_currencies:set[str]=set(); price_refs:set[str]=set()
    parity:dict[str,list[dict[str,Any]]]={}
    for item in value["plans"]:
        item=exact(item,{"ref","name","settlements","commercial","deploymentMode","entitlements","public"},{"trial","capabilityParityGroup"}); ref=c.ref("planRef",item["ref"])
        if ref in plans: raise ContractError("duplicate plan")
        if not isinstance(item["settlements"],list) or not 1<=len(item["settlements"])<=12: raise ContractError("plan without settlement option")
        intervals:set[str]=set()
        for option in item["settlements"]:
            price,currency,interval=settlement(c,option)
            if price in price_refs or interval in intervals: raise ContractError("duplicate settlement option")
            price_refs.add(price); intervals.add(interval); settlement_currencies.add(currency)
        plans[ref]=item
        if item["deploymentMode"] not in {"cloud","self-hosted","hybrid"}: raise ContractError("invalid deployment mode")
        if not item["entitlements"]: raise ContractError("plan without entitlements")
        for ent in item["entitlements"]: c.ref("entitlementRef",ent)
        model=item["commercial"]
        if not isinstance(model,dict) or "type" not in model: raise ContractError("missing commercial model")
        kind=model["type"]; metric: str|None=None
        if kind=="flat-subscription":
            exact(model,{"type"})
            if not intervals<={"month","year"}: raise ContractError("subscription settlement must recur")
        elif kind=="usage-subscription":
            model=exact(model,{"type","usageAllowance"}); metric=recurring_allowance(c,model["usageAllowance"])
            if not intervals<={"month","year"}: raise ContractError("usage subscription settlement must recur")
        elif kind=="prepaid-addon":
            model=exact(model,{"type","usageAllowance","compatiblePlanRefs"}); metric=prepaid_allowance(c,model["usageAllowance"])
            if intervals!={"one-time"} or len(item["settlements"])!=1 or not model["compatiblePlanRefs"]: raise ContractError("invalid prepaid commercial model")
            for compatible in model["compatiblePlanRefs"]: c.ref("planRef",compatible)
        elif kind=="perpetual-license":
            model=exact(model,{"type"},{"maintenance"})
            if intervals!={"one-time"} or len(item["settlements"])!=1 or item["deploymentMode"] not in {"self-hosted","hybrid"}: raise ContractError("invalid perpetual commercial model")
            if "maintenance" in model:
                maintenance=exact(model["maintenance"],{"settlement","includedPeriods","renewal"}); price,currency,interval=settlement(c,maintenance["settlement"])
                if price in price_refs: raise ContractError("duplicate maintenance price")
                price_refs.add(price); settlement_currencies.add(currency)
                if maintenance["settlement"]["interval"] not in {"month","year"} or not isinstance(maintenance["includedPeriods"],int) or not 0<=maintenance["includedPeriods"]<=10 or maintenance["renewal"] not in {"optional","automatic-after-notice"}: raise ContractError("invalid maintenance")
        else: raise ContractError("unsupported commercial model")
        commercial[ref]=(kind,metric)
        if "capabilityParityGroup" in item:
            parity.setdefault(c.ref("identifier",item["capabilityParityGroup"]),[]).append(item)
    for item in value["plans"]:
        if "trial" not in item: continue
        trial=exact(item["trial"],{"days","priceMinor","requiresPaymentMethod","conversionPlanRef","conversionMode","noticeDays","cancelBeforeCharge"})
        if not 1<=trial["days"]<=90 or trial["priceMinor"]!=0 or trial["cancelBeforeCharge"] is not True: raise ContractError("unsafe trial")
        if c.ref("planRef",trial["conversionPlanRef"]) not in plans or trial["conversionPlanRef"]==item["ref"]: raise ContractError("invalid trial conversion")
        if trial["conversionMode"]=="scheduled-after-notice" and trial["requiresPaymentMethod"] is not True: raise ContractError("scheduled charge lacks payment method policy")
    for ref,item in plans.items():
        kind,metric=commercial[ref]
        if kind!="prepaid-addon": continue
        for compatible in item["commercial"]["compatiblePlanRefs"]:
            if compatible not in commercial or commercial[compatible][0]!="usage-subscription": raise ContractError("prepaid add-on targets non-usage plan")
            if commercial[compatible][1]!=metric: raise ContractError("prepaid add-on metric mismatch")
    for group,items in parity.items():
        if len(items)<2: raise ContractError("capability parity group needs peers")
        expected=(tuple(sorted(items[0]["entitlements"])),items[0]["deploymentMode"],items[0]["commercial"]["type"])
        if any((tuple(sorted(item["entitlements"])),item["deploymentMode"],item["commercial"]["type"])!=expected for item in items[1:]): raise ContractError("capability parity mismatch")
    locales:set[str]=set(); display_currencies:set[str]=set()
    for default in value["localeDefaults"]:
        default=exact(default,{"locale","currency"})
        if not isinstance(default["locale"],str) or re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?",default["locale"]) is None or default["locale"] in locales: raise ContractError("invalid locale default")
        locales.add(default["locale"]); display_currencies.add(c.ref("currency",default["currency"]))
    pairs:set[tuple[str,str]]=set()
    for quote in value["displayQuotes"]:
        quote=exact(quote,{"baseCurrency","quoteCurrency","rateNumerator","rateDenominator","asOf","indicative"}); base=c.ref("currency",quote["baseCurrency"]); target=c.ref("currency",quote["quoteCurrency"]); pair=(base,target)
        if base==target or pair in pairs or quote["indicative"] is not True or quote["rateNumerator"]<1 or quote["rateDenominator"]<1: raise ContractError("invalid display quote")
        pairs.add(pair)
        try: date.fromisoformat(quote["asOf"])
        except (TypeError,ValueError) as error: raise ContractError("invalid quote date") from error
    for base in settlement_currencies:
        for target in display_currencies:
            if base!=target and (base,target) not in pairs: raise ContractError("display conversion coverage missing")


def validate_request(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","requestId","operation","accountRef","tenantRef","planRef","priceRef","billingRef","intentRef","grantRef","planHash"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-lifecycle-request/v1": raise ContractError("unsupported request")
    c.ref("identifier",value["requestId"])
    if value["operation"] not in {"inspect","signup","select_plan","start_trial","confirm_subscription","purchase_addon","request_plan_change","cancel"}: raise ContractError("unsupported operation")
    for name in ("accountRef","tenantRef","planRef","priceRef","billingRef","intentRef","grantRef","sha256"):
        c.ref(name,value["planHash"] if name=="sha256" else value[name])


def validate_lifecycle(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","accountRef","tenantRef","currentPlanRef","state","version","updatedAt","events","usageGrants"},{"trial","subscription","provisioning"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-lifecycle-state/v1": raise ContractError("unsupported state")
    c.ref("accountRef",value["accountRef"]); c.ref("tenantRef",value["tenantRef"]); c.ref("planRef",value["currentPlanRef"]); time_value(value["updatedAt"])
    if value["state"] in {"trial_active","trial_expiring"} and "trial" not in value: raise ContractError("trial state missing")
    if value["state"] in {"paid_pending_provisioning","active","plan_change_pending","suspended"} and "subscription" not in value: raise ContractError("subscription missing")
    if value["state"] in {"paid_pending_provisioning","active","plan_change_pending"} and "provisioning" not in value: raise ContractError("provisioning missing")
    if "trial" in value:
        trial=exact(value["trial"],{"startedAt","endsAt","conversionPlanRef","conversionMode","noticeAt","paymentMethodPresent","cancelledAt"})
        start,end,notice=time_value(trial["startedAt"]),time_value(trial["endsAt"]),time_value(trial["noticeAt"])
        if not start<notice<end: raise ContractError("invalid trial chronology")
        c.ref("planRef",trial["conversionPlanRef"])
        if trial["conversionMode"]=="scheduled-after-notice" and trial["paymentMethodPresent"] is not True: raise ContractError("scheduled conversion not eligible")
    if "subscription" in value:
        sub=exact(value["subscription"],{"providerRef","billingRef","providerPlanRef","status","verificationMode","verifiedAt","settlement"})
        c.ref("providerRef",sub["providerRef"]); c.ref("billingRef",sub["billingRef"]); c.ref("billingRef",sub["providerPlanRef"]); time_value(sub["verifiedAt"]); settlement(c,sub["settlement"])
        if sub["verificationMode"]!="server-side": raise ContractError("client-trusted subscription")
        if value["state"]=="active" and sub["status"]!="active": raise ContractError("active account has inactive subscription")
    if "provisioning" in value:
        p=exact(value["provisioning"],{"outboxRef","idempotencyKey","deploymentRef","state","attempts","updatedAt"},{"externalRef","errorEvidenceRef"})
        c.ref("outboxRef",p["outboxRef"]); c.ref("identifier",p["idempotencyKey"]); c.ref("deploymentRef",p["deploymentRef"]); time_value(p["updatedAt"])
        if not 0<=p["attempts"]<=20: raise ContractError("provision attempts out of range")
        if p["state"]=="completed" and "externalRef" not in p: raise ContractError("completed provisioning lacks resource")
        if p["state"]=="failed" and "errorEvidenceRef" not in p: raise ContractError("failed provisioning lacks evidence")
        if value["state"]=="active" and p["state"]!="completed": raise ContractError("active account not provisioned")
    seen_event:set[str]=set(); seen_key:set[str]=set()
    for event in value["events"]:
        event=exact(event,{"eventRef","type","digest","idempotencyKey","signatureVerified","verifiedAt","processedAt"})
        ref=c.ref("eventRef",event["eventRef"]); key=c.ref("identifier",event["idempotencyKey"])
        if ref in seen_event or key in seen_key: raise ContractError("duplicate billing event")
        seen_event.add(ref); seen_key.add(key); c.ref("sha256Ref",event["digest"])
        if event["signatureVerified"] is not True or time_value(event["processedAt"])<time_value(event["verifiedAt"]): raise ContractError("unverified event")
    seen_grants:set[tuple[str,str,str,str]]=set()
    for grant in value["usageGrants"]:
        grant=exact(grant,{"sourcePlanRef","priceRef","metricRef","unitsGranted","unitsRemaining","validFrom","expiresAt","billingRef","verificationMode","verifiedAt"})
        source=c.ref("planRef",grant["sourcePlanRef"]); price=c.ref("priceRef",grant["priceRef"]); metric=c.ref("metricRef",grant["metricRef"]); billing=c.ref("billingRef",grant["billingRef"])
        identity=(source,price,metric,billing)
        if identity in seen_grants: raise ContractError("duplicate usage grant")
        seen_grants.add(identity)
        if not isinstance(grant["unitsGranted"],int) or not isinstance(grant["unitsRemaining"],int) or not 0<=grant["unitsRemaining"]<=grant["unitsGranted"] or grant["unitsGranted"]<1: raise ContractError("invalid usage grant units")
        verified=time_value(grant["verifiedAt"]); valid=time_value(grant["validFrom"]); expires=time_value(grant["expiresAt"])
        if grant["verificationMode"]!="server-side" or not verified<=valid<expires: raise ContractError("unverified usage grant")


def validate_receipt(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","requestId","accountRef","tenantRef","planRef","priceRef","inputHash","planHash","outcome","startedAt","completedAt","evidenceRefs","secretsRedacted","paymentDataStored"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-lifecycle-receipt/v1": raise ContractError("unsupported receipt")
    c.ref("identifier",value["requestId"]); c.ref("accountRef",value["accountRef"]); c.ref("tenantRef",value["tenantRef"]); c.ref("planRef",value["planRef"]); c.ref("priceRef",value["priceRef"]); c.ref("sha256",value["inputHash"]); c.ref("sha256",value["planHash"])
    if time_value(value["completedAt"])<time_value(value["startedAt"]): raise ContractError("receipt chronology")
    if value["outcome"] not in {"denied","accepted","trial_started","billing_pending","billing_verified","provisioning_queued","activated","addon_activated","cancelled","failed"}: raise ContractError("unsupported receipt outcome")
    if not value["evidenceRefs"]: raise ContractError("receipt lacks evidence")
    for ref in value["evidenceRefs"]: c.ref("evidenceRef",ref)
    if value["secretsRedacted"] is not True or value["paymentDataStored"] is not False: raise ContractError("unsafe receipt")


def uri(value:Any)->str:
    if not isinstance(value,str) or len(value)>512 or re.fullmatch(r"[a-z][a-z0-9+.-]*://\S+",value) is None: raise ContractError("invalid URI reference")
    return value


def safe_pointer(value:Any)->str:
    if not isinstance(value,str) or len(value)>384 or not value.startswith("/"): raise ContractError("invalid JSON Pointer")
    for encoded in value.split("/")[1:]:
        segment=encoded.replace("~1","/").replace("~0","~")
        if UNSAFE_POINTER_SEGMENT.fullmatch(segment): raise ContractError("unsafe pointer channel")
    return value


def retry_policy(value:Any)->None:
    value=exact(value,{"maxAttempts","backoff","retryableOutcomes","terminalOutcomes"})
    if type(value["maxAttempts"]) is not int or not 1<=value["maxAttempts"]<=20: raise ContractError("unbounded adapter retries")
    if value["backoff"] not in {"none","bounded-exponential"}: raise ContractError("invalid adapter backoff")
    retryable={"timeout","rate-limited","provider-unavailable","pending"}; terminal={"verified","denied","failed","cancelled","exhausted"}
    if not isinstance(value["retryableOutcomes"],list) or len(value["retryableOutcomes"])!=len(set(value["retryableOutcomes"])) or not set(value["retryableOutcomes"])<=retryable: raise ContractError("invalid retry outcomes")
    if not isinstance(value["terminalOutcomes"],list) or len(value["terminalOutcomes"])!=len(set(value["terminalOutcomes"])) or not {"verified","denied","failed"}<=set(value["terminalOutcomes"])<=terminal: raise ContractError("invalid terminal outcomes")


def evidence_policy(value:Any)->None:
    value=exact(value,{"providerPayload","lifecycleReceipt","authorizationMaterial","personalData"})
    expected={"providerPayload":"separate-evidence-store","lifecycleReceipt":"references-and-digests-only","authorizationMaterial":"external-binding-only","personalData":"minimized"}
    if value!=expected: raise ContractError("unsafe adapter evidence policy")


def adapter_operation(value:Any)->tuple[str,str]:
    value=exact(value,{"id","effect","contractRef","requestMappings","evidenceMappings","idempotency"})
    if not isinstance(value["id"],str) or re.fullmatch(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*",value["id"]) is None: raise ContractError("invalid operation id")
    if value["effect"] not in {"query","command","verification"}: raise ContractError("invalid operation effect")
    uri(value["contractRef"])
    request_targets:set[str]=set()
    for mapping in value["requestMappings"]:
        mapping=exact(mapping,{"source","targetPointer","transform"}); target=safe_pointer(mapping["targetPointer"])
        if target in request_targets: raise ContractError("duplicate request mapping")
        request_targets.add(target)
        if mapping["source"] not in {"accountRef","tenantRef","planRef","priceRef","providerPlanRef","amountMinor","currency","billingRef","providerResourceId","requestId","eventRef","deploymentRef","planHash","grantRef","idempotencyKey"}: raise ContractError("invalid request source")
        if mapping["transform"] not in {"identity","registry-lookup","minor-to-decimal-string","decimal-string-to-minor","uppercase","lowercase","opaque-reference","unix-seconds-to-date-time","sha256"}: raise ContractError("invalid mapping transform")
    evidence_targets:set[str]=set()
    if not isinstance(value["evidenceMappings"],list) or not value["evidenceMappings"]: raise ContractError("operation lacks evidence mapping")
    for mapping in value["evidenceMappings"]:
        mapping=exact(mapping,{"sourceKind","sourcePointer","target","transform"}); safe_pointer(mapping["sourcePointer"])
        if mapping["sourceKind"] not in {"provider-response","verified-event","provider-plan-registry","request-ledger","deployment-verifier"}: raise ContractError("invalid evidence source")
        if mapping["target"] in evidence_targets: raise ContractError("duplicate evidence mapping")
        evidence_targets.add(mapping["target"])
        if mapping["target"] not in {"accountRef","tenantRef","planRef","priceRef","providerPlanRef","amountMinor","currency","billingRef","providerStatus","requestId","eventRef","eventType","occurredAt","deploymentRef","planHash","grantRef","resourceRef","evidenceRef"}: raise ContractError("invalid evidence target")
        if mapping["transform"] not in {"identity","registry-lookup","minor-to-decimal-string","decimal-string-to-minor","uppercase","lowercase","opaque-reference","unix-seconds-to-date-time","sha256"}: raise ContractError("invalid evidence transform")
    idem=exact(value["idempotency"],{"required","keySource"})
    if type(idem["required"]) is not bool or idem["keySource"] not in {"none","request-id","event-id","outbox-id"}: raise ContractError("invalid idempotency binding")
    if value["effect"] in {"command","verification"} and (idem["required"] is not True or idem["keySource"]=="none"): raise ContractError("mutating operation lacks idempotency")
    if value["effect"]=="query" and (idem["required"] is not False or idem["keySource"]!="none"): raise ContractError("query has mutating idempotency")
    return value["id"],value["effect"]


def validate_payment_profile(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","profileRef","version","adapterRef","providerRef","upstreamContracts","operations","requiredBindings","eventBindings","verification","reconciliation","retryPolicy","evidencePolicy"})
    if value["$schema"]!=PROFILE_SCHEMA_URI or value["schema"]!="wellmanifest.saas-payment-adapter-profile/v1": raise ContractError("unsupported payment profile")
    for ref in (value["profileRef"],value["adapterRef"],value["providerRef"]): uri(ref)
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+",value["version"]) is None: raise ContractError("invalid profile version")
    if not isinstance(value["upstreamContracts"],list) or not value["upstreamContracts"] or len(value["upstreamContracts"])!=len(set(value["upstreamContracts"])): raise ContractError("invalid upstream contracts")
    for ref in value["upstreamContracts"]: uri(ref)
    operations=dict(adapter_operation(item) for item in value["operations"])
    expected={"create_subscription","inspect_subscription","cancel_subscription","create_payment","inspect_payment","capture_payment","verify_event"}
    if set(operations)!=expected or len(operations)!=len(value["operations"]): raise ContractError("payment operation set incomplete")
    effects={"create_subscription":"command","inspect_subscription":"query","cancel_subscription":"command","create_payment":"command","inspect_payment":"query","capture_payment":"command","verify_event":"verification"}
    if operations!=effects: raise ContractError("payment operation effect mismatch")
    bindings={"accountRef","tenantRef","planRef","priceRef","amountMinor","currency","providerStatus"}
    if set(value["requiredBindings"])!=bindings or len(value["requiredBindings"])!=len(bindings): raise ContractError("payment verification bindings incomplete")
    provider_events:set[str]=set()
    if not isinstance(value["eventBindings"],list) or len(value["eventBindings"])<4: raise ContractError("payment event mappings incomplete")
    for item in value["eventBindings"]:
        item=exact(item,{"providerEvent","lifecycleSignal","eventIdPointer","resourcePointer","requiresInspection"})
        if not isinstance(item["providerEvent"],str) or item["providerEvent"] in provider_events: raise ContractError("duplicate provider event")
        provider_events.add(item["providerEvent"]); safe_pointer(item["eventIdPointer"]); safe_pointer(item["resourcePointer"])
        if item["lifecycleSignal"] not in {"reconcile_subscription","reconcile_payment","subscription_activated","subscription_suspended","subscription_cancelled","addon_payment_completed","payment_denied"}: raise ContractError("invalid lifecycle signal")
        if item["requiresInspection"] is not True: raise ContractError("provider event trusted without inspection")
    verification=exact(value["verification"],{"mode","contractRef","operationId","requiredInputs","successPredicate","failureOutcome","payloadRetention"}); uri(verification["contractRef"])
    if verification["mode"] not in {"provider-api","local-signature"} or verification["operationId"]!="verify_event" or verification["failureOutcome"]!="denied" or verification["payloadRetention"]!="digest-only": raise ContractError("unsafe event verification")
    inputs=set(verification["requiredInputs"])
    if len(inputs)!=len(verification["requiredInputs"]) or not {"raw-body","transport-signature","configured-verifier-binding"}<=inputs<={"raw-body","transport-signature","configured-verifier-binding","provider-certificate-metadata"}: raise ContractError("verification inputs incomplete")
    predicate=exact(verification["successPredicate"],{"source","equals"},{"pointer"})
    if predicate["source"]=="operation-result":
        if "pointer" not in predicate or safe_pointer(predicate["pointer"])!="/verification_status" or predicate["equals"]!="SUCCESS": raise ContractError("invalid provider verification predicate")
    elif predicate["source"]=="verified-call-return":
        if "pointer" in predicate or predicate["equals"]!="verified": raise ContractError("invalid local verification predicate")
    else: raise ContractError("unsupported verification predicate")
    reconciliation=exact(value["reconciliation"],{"subscriptionInspectOperationId","paymentInspectOperationId","unknownEventOutcome","outOfOrder","staleEvent"})
    if reconciliation!={"subscriptionInspectOperationId":"inspect_subscription","paymentInspectOperationId":"inspect_payment","unknownEventOutcome":"quarantine","outOfOrder":"inspect-authoritative-resource","staleEvent":"no-transition"}: raise ContractError("unsafe payment reconciliation")
    retry_policy(value["retryPolicy"]); evidence_policy(value["evidencePolicy"])


def validate_deployment_profile(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","profileRef","version","adapterRef","upstreamContracts","operations","requiredBindings","authorization","activationBoundary","outbox","coordinatePolicy","retryPolicy","evidencePolicy"})
    if value["$schema"]!=PROFILE_SCHEMA_URI or value["schema"]!="wellmanifest.saas-deployment-adapter-profile/v1": raise ContractError("unsupported deployment profile")
    for ref in (value["profileRef"],value["adapterRef"]): uri(ref)
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+",value["version"]) is None: raise ContractError("invalid profile version")
    if not isinstance(value["upstreamContracts"],list) or not value["upstreamContracts"] or len(value["upstreamContracts"])!=len(set(value["upstreamContracts"])): raise ContractError("invalid deployment contracts")
    for ref in value["upstreamContracts"]: uri(ref)
    operations=dict(adapter_operation(item) for item in value["operations"])
    effects={"compile":"query","authorize":"command","apply":"command","verify":"verification","rollback":"command"}
    if operations!=effects or len(operations)!=len(value["operations"]): raise ContractError("deployment operation set incomplete")
    bindings={"accountRef","tenantRef","planRef","deploymentRef","planHash","grantRef","idempotencyKey"}
    if set(value["requiredBindings"])!=bindings or len(value["requiredBindings"])!=len(bindings): raise ContractError("deployment bindings incomplete")
    authorization=exact(value["authorization"],{"mode","operationId","persistGrant","denialOutcome"})
    if authorization!={"mode":"single-use-external-grant","operationId":"authorize","persistGrant":False,"denialOutcome":"denied"}: raise ContractError("unsafe deployment authorization")
    activation=exact(value["activationBoundary"],{"requiresApplyAndVerify","verifyOperationId","successOutcome","mismatchOutcome"})
    if activation!={"requiresApplyAndVerify":True,"verifyOperationId":"verify","successOutcome":"activated","mismatchOutcome":"failed"}: raise ContractError("unsafe deployment activation")
    outbox=exact(value["outbox"],{"durable","reuseIdempotencyKey","claimMode"})
    if outbox!={"durable":True,"reuseIdempotencyKey":True,"claimMode":"single-worker-lease"}: raise ContractError("unsafe deployment outbox")
    coordinates=exact(value["coordinatePolicy"],{"profileContainsCoordinates","resolution","receipt"})
    if coordinates!={"profileContainsCoordinates":False,"resolution":"external-deployment-binding","receipt":"resource-reference-only"}: raise ContractError("raw deployment coordinates")
    retry_policy(value["retryPolicy"]); evidence_policy(value["evidencePolicy"])


def validate_profile_examples(c:Contracts)->list[dict[str,Any]]:
    examples=exact(c.profile_examples,{"schema","profiles"})
    if examples["schema"]!="wellmanifest.saas-adapter-profile-examples/v1" or not isinstance(examples["profiles"],list): raise ContractError("invalid profile examples")
    profile_refs:set[str]=set(); adapter_refs:set[str]=set(); providers:set[str]=set(); deployment_count=0
    for profile in examples["profiles"]:
        if profile.get("schema")=="wellmanifest.saas-payment-adapter-profile/v1":
            validate_payment_profile(c,profile); providers.add(profile["providerRef"])
        elif profile.get("schema")=="wellmanifest.saas-deployment-adapter-profile/v1":
            validate_deployment_profile(c,profile); deployment_count+=1
        else: raise ContractError("unknown profile example")
        if profile["profileRef"] in profile_refs or profile["adapterRef"] in adapter_refs: raise ContractError("duplicate adapter profile identity")
        profile_refs.add(profile["profileRef"]); adapter_refs.add(profile["adapterRef"])
    if len(providers)<2 or deployment_count<1: raise ContractError("provider neutrality evidence incomplete")
    return examples["profiles"]


def run_all()->dict[str,Any]:
    c=Contracts(); c.integrity(); offer,request,state,receipt=offer_example(),request_example(),lifecycle_example(),receipt_example()
    validate_offer(c,offer); validate_request(c,request); validate_lifecycle(c,state); validate_receipt(c,receipt)
    profiles=validate_profile_examples(c); paypal,stripe,deployment=profiles
    cases=[]
    def add(name:str,validator:Any,value:Any)->None:
        cases.append((name,lambda validator=validator,value=value:validator(c,value)))
    bad=copy.deepcopy(offer); bad["plans"][0]["trial"].pop("conversionPlanRef"); add("trial-no-conversion",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][0]["trial"]["cancelBeforeCharge"]=False; add("trial-no-cancel-boundary",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][0]["trial"]["conversionMode"]="scheduled-after-notice"; add("scheduled-no-payment-method",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["displayQuotes"][0]["indicative"]=False; add("authoritative-display-rate",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][2]["entitlements"]=["entitlement://example.test/subactor/pro-only/v1"]; add("false-capability-parity",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][3]["settlements"][0]["interval"]="month"; add("recurring-prepaid-charge",validate_offer,bad)
    bad=copy.deepcopy(offer); duplicate=copy.deepcopy(bad["plans"][1]["settlements"][0]); duplicate["priceRef"]="price://example.test/basic/month-promo/v1"; bad["plans"][1]["settlements"].append(duplicate); add("duplicate-billing-interval",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][2]["settlements"][0]["priceRef"]="price://example.test/basic/month/v1"; add("duplicate-price-reference",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][3]["commercial"]["usageAllowance"].pop("validityDays"); add("prepaid-without-expiry",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][3]["commercial"]["compatiblePlanRefs"]=["plan://example.test/trial/v1"]; add("prepaid-targets-flat-plan",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][3]["commercial"]["usageAllowance"]["metricRef"]="metric://example.test/api/calls/v1"; add("prepaid-metric-mismatch",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["plans"][4]["deploymentMode"]="cloud"; add("cloud-perpetual-license",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["localeDefaults"].append({"locale":"pl","currency":"EUR"}); add("duplicate-locale-default",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["displayQuotes"].pop(); add("missing-display-coverage",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["displayQuotes"].append(copy.deepcopy(bad["displayQuotes"][0])); add("duplicate-display-pair",validate_offer,bad)
    bad=copy.deepcopy(offer); bad["displayQuotes"][0]["quoteCurrency"]="PLN"; add("identity-display-rate",validate_offer,bad)
    bad=copy.deepcopy(request); bad["paymentStatus"]="COMPLETED"; add("client-payment-status",validate_request,bad)
    bad=copy.deepcopy(request); bad["card_token"]="redacted-canary"; add("payment-credential",validate_request,bad)
    bad=copy.deepcopy(request); bad["hostname"]="acme.example.test"; add("raw-tenant-coordinate",validate_request,bad)
    bad=copy.deepcopy(request); bad.pop("priceRef"); add("implicit-price-selection",validate_request,bad)
    bad=copy.deepcopy(state); bad["events"][0]["signatureVerified"]=False; add("unsigned-event",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["events"].append(copy.deepcopy(bad["events"][0])); add("duplicate-event",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["subscription"]["verificationMode"]="browser-callback"; add("client-trusted-subscription",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad.pop("subscription"); add("active-without-subscription",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["provisioning"]["state"]="pending"; bad["provisioning"].pop("externalRef"); add("active-before-provisioned",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["provisioning"]["attempts"]=21; add("unbounded-provisioning",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["usageGrants"][0]["verificationMode"]="browser-callback"; add("client-issued-usage-grant",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["usageGrants"][0]["unitsRemaining"]=10001; add("usage-grant-overdraw",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["usageGrants"][0]["expiresAt"]="2026-08-11T11:58:00Z"; add("usage-grant-invalid-expiry",validate_lifecycle,bad)
    bad=copy.deepcopy(state); bad["usageGrants"].append(copy.deepcopy(bad["usageGrants"][0])); add("duplicate-usage-grant",validate_lifecycle,bad)
    bad=copy.deepcopy(receipt); bad["providerPayload"]={"status":"ACTIVE"}; add("provider-payload-receipt",validate_receipt,bad)
    bad=copy.deepcopy(receipt); bad["paymentDataStored"]=True; add("payment-data-receipt",validate_receipt,bad)
    bad=copy.deepcopy(paypal); bad["operations"].append(copy.deepcopy(bad["operations"][0])); add("duplicate-payment-operation",validate_payment_profile,bad)
    bad=copy.deepcopy(paypal); bad["operations"]=[item for item in bad["operations"] if item["id"]!="verify_event"]; add("payment-without-event-verifier",validate_payment_profile,bad)
    bad=copy.deepcopy(paypal); bad["operations"][0]["idempotency"]={"required":False,"keySource":"none"}; add("non-idempotent-payment-command",validate_payment_profile,bad)
    bad=copy.deepcopy(paypal); bad["verification"]["successPredicate"].pop("pointer"); add("provider-verification-without-predicate",validate_payment_profile,bad)
    bad=copy.deepcopy(paypal); bad["eventBindings"].append(copy.deepcopy(bad["eventBindings"][0])); add("duplicate-provider-event",validate_payment_profile,bad)
    bad=copy.deepcopy(stripe); bad["eventBindings"][0]["requiresInspection"]=False; add("event-trusted-without-inspection",validate_payment_profile,bad)
    bad=copy.deepcopy(stripe); bad["operations"][3]["requestMappings"][0]["targetPointer"]="/card/number"; add("payment-secret-pointer",validate_payment_profile,bad)
    bad=copy.deepcopy(deployment); bad["operations"][2]["requestMappings"][0]["targetPointer"]="/hostname"; add("deployment-coordinate-pointer",validate_deployment_profile,bad)
    bad=copy.deepcopy(deployment); bad["retryPolicy"]["maxAttempts"]=21; add("unbounded-adapter-retries",validate_deployment_profile,bad)
    bad=copy.deepcopy(deployment); bad["authorization"]["persistGrant"]=True; add("persisted-deployment-grant",validate_deployment_profile,bad)
    bad=copy.deepcopy(deployment); bad["activationBoundary"]["requiresApplyAndVerify"]=False; add("activation-without-verification",validate_deployment_profile,bad)
    bad=copy.deepcopy(deployment); bad["outbox"]["durable"]=False; add("non-durable-deployment-outbox",validate_deployment_profile,bad)
    bad=copy.deepcopy(deployment); bad["evidencePolicy"]["lifecycleReceipt"]="raw-provider-payload"; add("provider-payload-in-lifecycle-receipt",validate_deployment_profile,bad)
    rejected=[]
    for name,case in cases:
        try: case()
        except (ContractError,KeyError,TypeError): rejected.append(name)
        else: raise AssertionError(f"adversarial case accepted: {name}")
    return {"schema":"wellmanifest.saas-lifecycle-conformance/v1","ok":True,"schemaDigest":"sha256:"+SCHEMA_DIGEST,"grammarDigest":"sha256:"+GRAMMAR_DIGEST,"profileSchemaDigest":"sha256:"+PROFILE_SCHEMA_DIGEST,"profileExamplesDigest":"sha256:"+PROFILE_EXAMPLES_DIGEST,"positiveVariants":4,"adapterProfileVariants":len(profiles),"adversarialRejected":rejected}


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--all",action="store_true"); args=p.parse_args()
    if not args.all: p.error("--all is required")
    print(json.dumps(run_all(),indent=2,sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
