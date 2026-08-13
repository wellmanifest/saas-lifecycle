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
SCHEMA_DIGEST = "23719fdcd10049c25540057afb7243751f159ef9abfaaa0a34d4464622beb112"
GRAMMAR_DIGEST = "b2c5d381ee30d73e8f15a3da505328c0fc59835fcb77e68004d7e5da750ab30f"
SCHEMA_URI = "https://wellmanifest.dev/schemas/saas-lifecycle/v1"
SENSITIVE = re.compile(r"(?:password|passwd|token|secret|cookie|api[-_]?key|card|cvv|private[-_]?key|webhook[-_]?signature)", re.I)
SAFE_ASSERTIONS = {"secretsRedacted", "paymentDataStored", "signatureVerified"}


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
        defs=self.schema.get("$defs", {})
        names=("identifier","sha256","sha256Ref","accountRef","tenantRef","planRef","providerRef","billingRef","intentRef","grantRef","eventRef","evidenceRef","outboxRef","deploymentRef","entitlementRef","currency")
        self.patterns={name:re.compile(defs[name]["pattern"]) for name in names}

    def ref(self,name:str,value:Any)->str:
        if not isinstance(value,str) or self.patterns[name].fullmatch(value) is None: raise ContractError(f"invalid {name}")
        return value

    def integrity(self)->None:
        if self.schema.get("$schema")!="https://json-schema.org/draft/2020-12/schema" or self.schema.get("$id")!=SCHEMA_URI: raise ContractError("schema identity mismatch")
        if digest(canonical(self.schema))!=SCHEMA_DIGEST or digest(self.grammar)!=GRAMMAR_DIGEST: raise ContractError("contract digest mismatch")
        if {x.get("$ref") for x in self.schema.get("oneOf",[])}!={"#/$defs/offer","#/$defs/request","#/$defs/lifecycle","#/$defs/receipt"}: raise ContractError("document variants incomplete")
        for fragment in ("root ::= request","payment status","plan-ref ::=","billing-ref ::=","sha256 ::="):
            if fragment not in self.grammar: raise ContractError("grammar incomplete")
        self._closed(self.schema)

    def _closed(self,value:Any)->None:
        if isinstance(value,dict):
            if value.get("type")=="object" and value.get("additionalProperties") is not False: raise ContractError("open object schema")
            for child in value.values(): self._closed(child)
        elif isinstance(value,list):
            for child in value: self._closed(child)


def offer_example()->dict[str,Any]:
    starter="plan://example.test/starter/v1"
    return {
        "$schema":SCHEMA_URI,"schema":"wellmanifest.saas-offer/v1","offerId":"offer-2026-08","version":"1.0.0",
        "plans":[
            {"ref":"plan://example.test/trial/v1","name":"30 day trial","settlement":{"currency":"EUR","amountMinor":0,"interval":"month","authoritative":True},"entitlements":["entitlement://example.test/subactor/starter/v1"],"trial":{"days":30,"priceMinor":0,"requiresPaymentMethod":False,"conversionPlanRef":starter,"conversionMode":"explicit-accept","noticeDays":7,"cancelBeforeCharge":True},"public":True},
            {"ref":starter,"name":"Starter","settlement":{"currency":"EUR","amountMinor":4900,"interval":"month","authoritative":True},"entitlements":["entitlement://example.test/subactor/starter/v1"],"public":True},
        ],
        "displayQuotes":[{"currency":"PLN","rateNumerator":425,"rateDenominator":100,"asOf":"2026-08-12","indicative":True}],
        "legalPolicyRef":"policy://example.test/saas/terms/v1",
    }


def request_example()->dict[str,Any]:
    return {"$schema":SCHEMA_URI,"schema":"wellmanifest.saas-lifecycle-request/v1","requestId":"request-001","operation":"start_trial","accountRef":"account://example.test/account-001","tenantRef":"tenant://example.test/acme","planRef":"plan://example.test/trial/v1","billingRef":"billing://example.test/accounts/account-001/none","intentRef":"intent://example.test/onboarding/request-001","grantRef":"grant://example.test/onboarding/request-001/g1","planHash":"a"*64}


def lifecycle_example()->dict[str,Any]:
    return {
        "$schema":SCHEMA_URI,"schema":"wellmanifest.saas-lifecycle-state/v1","accountRef":"account://example.test/account-001","tenantRef":"tenant://example.test/acme","currentPlanRef":"plan://example.test/starter/v1","state":"active","version":7,"updatedAt":"2026-08-12T12:00:00Z",
        "subscription":{"providerRef":"provider://example.test/paypal","billingRef":"billing://example.test/subscriptions/sub-001","providerPlanRef":"billing://example.test/plans/starter","status":"active","verificationMode":"server-side","verifiedAt":"2026-08-12T11:58:00Z","settlement":{"currency":"EUR","amountMinor":4900,"interval":"month","authoritative":True}},
        "provisioning":{"outboxRef":"outbox://example.test/provisioning/item-001","idempotencyKey":"account-001-starter-v1","deploymentRef":"deployment://example.test/tenant/acme/v1","state":"completed","attempts":1,"updatedAt":"2026-08-12T12:00:00Z","externalRef":"resource://example.test/tenants/acme"},
        "events":[{"eventRef":"event://example.test/paypal/event-001","type":"subscription_activated","digest":"sha256:"+"b"*64,"idempotencyKey":"event-001","signatureVerified":True,"verifiedAt":"2026-08-12T11:57:00Z","processedAt":"2026-08-12T11:58:00Z"}],
    }


def receipt_example()->dict[str,Any]:
    return {"$schema":SCHEMA_URI,"schema":"wellmanifest.saas-lifecycle-receipt/v1","requestId":"request-001","accountRef":"account://example.test/account-001","tenantRef":"tenant://example.test/acme","planRef":"plan://example.test/starter/v1","inputHash":"c"*64,"planHash":"a"*64,"outcome":"activated","startedAt":"2026-08-12T11:50:00Z","completedAt":"2026-08-12T12:00:00Z","evidenceRefs":["evidence://example.test/saas/activation-001/r1"],"secretsRedacted":True,"paymentDataStored":False}


def settlement(c:Contracts,value:Any)->None:
    value=exact(value,{"currency","amountMinor","interval","authoritative"}); c.ref("currency",value["currency"])
    if not isinstance(value["amountMinor"],int) or value["amountMinor"]<0 or value["authoritative"] is not True: raise ContractError("invalid settlement")


def validate_offer(c:Contracts,value:Any)->None:
    value=exact(value,{"$schema","schema","offerId","version","plans","displayQuotes","legalPolicyRef"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-offer/v1": raise ContractError("unsupported offer")
    c.ref("identifier",value["offerId"])
    plans:set[str]=set()
    for item in value["plans"]:
        item=exact(item,{"ref","name","settlement","entitlements","public"},{"trial"}); ref=c.ref("planRef",item["ref"])
        if ref in plans: raise ContractError("duplicate plan")
        plans.add(ref); settlement(c,item["settlement"])
        if not item["entitlements"]: raise ContractError("plan without entitlements")
        for ent in item["entitlements"]: c.ref("entitlementRef",ent)
    for item in value["plans"]:
        if "trial" not in item: continue
        trial=exact(item["trial"],{"days","priceMinor","requiresPaymentMethod","conversionPlanRef","conversionMode","noticeDays","cancelBeforeCharge"})
        if not 1<=trial["days"]<=90 or trial["priceMinor"]!=0 or trial["cancelBeforeCharge"] is not True: raise ContractError("unsafe trial")
        if c.ref("planRef",trial["conversionPlanRef"]) not in plans or trial["conversionPlanRef"]==item["ref"]: raise ContractError("invalid trial conversion")
        if trial["conversionMode"]=="scheduled-after-notice" and trial["requiresPaymentMethod"] is not True: raise ContractError("scheduled charge lacks payment method policy")
    currencies:set[str]=set()
    for quote in value["displayQuotes"]:
        quote=exact(quote,{"currency","rateNumerator","rateDenominator","asOf","indicative"}); currency=c.ref("currency",quote["currency"])
        if currency in currencies or quote["indicative"] is not True or quote["rateNumerator"]<1 or quote["rateDenominator"]<1: raise ContractError("invalid display quote")
        currencies.add(currency)
        try: date.fromisoformat(quote["asOf"])
        except (TypeError,ValueError) as error: raise ContractError("invalid quote date") from error


def validate_request(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","requestId","operation","accountRef","tenantRef","planRef","billingRef","intentRef","grantRef","planHash"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-lifecycle-request/v1": raise ContractError("unsupported request")
    c.ref("identifier",value["requestId"])
    if value["operation"] not in {"inspect","signup","select_plan","start_trial","confirm_subscription","request_plan_change","cancel"}: raise ContractError("unsupported operation")
    for name in ("accountRef","tenantRef","planRef","billingRef","intentRef","grantRef","sha256"):
        c.ref(name,value["planHash"] if name=="sha256" else value[name])


def validate_lifecycle(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","accountRef","tenantRef","currentPlanRef","state","version","updatedAt","events"},{"trial","subscription","provisioning"})
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


def validate_receipt(c:Contracts,value:Any)->None:
    reject_sensitive(value); value=exact(value,{"$schema","schema","requestId","accountRef","tenantRef","planRef","inputHash","planHash","outcome","startedAt","completedAt","evidenceRefs","secretsRedacted","paymentDataStored"})
    if value["$schema"]!=SCHEMA_URI or value["schema"]!="wellmanifest.saas-lifecycle-receipt/v1": raise ContractError("unsupported receipt")
    c.ref("identifier",value["requestId"]); c.ref("accountRef",value["accountRef"]); c.ref("tenantRef",value["tenantRef"]); c.ref("planRef",value["planRef"]); c.ref("sha256",value["inputHash"]); c.ref("sha256",value["planHash"])
    if time_value(value["completedAt"])<time_value(value["startedAt"]): raise ContractError("receipt chronology")
    if not value["evidenceRefs"]: raise ContractError("receipt lacks evidence")
    for ref in value["evidenceRefs"]: c.ref("evidenceRef",ref)
    if value["secretsRedacted"] is not True or value["paymentDataStored"] is not False: raise ContractError("unsafe receipt")


def run_all()->dict[str,Any]:
    c=Contracts(); c.integrity(); offer,request,state,receipt=offer_example(),request_example(),lifecycle_example(),receipt_example()
    validate_offer(c,offer); validate_request(c,request); validate_lifecycle(c,state); validate_receipt(c,receipt)
    cases=[]
    bad=copy.deepcopy(offer); bad["plans"][0]["trial"].pop("conversionPlanRef"); cases.append(("trial-no-conversion",lambda:validate_offer(c,bad)))
    bad=copy.deepcopy(offer); bad["plans"][0]["trial"]["cancelBeforeCharge"]=False; cases.append(("trial-no-cancel-boundary",lambda:validate_offer(c,bad)))
    bad=copy.deepcopy(offer); bad["plans"][0]["trial"]["conversionMode"]="scheduled-after-notice"; cases.append(("scheduled-no-payment-method",lambda:validate_offer(c,bad)))
    bad=copy.deepcopy(offer); bad["displayQuotes"][0]["indicative"]=False; cases.append(("authoritative-display-rate",lambda:validate_offer(c,bad)))
    bad=copy.deepcopy(request); bad["paymentStatus"]="COMPLETED"; cases.append(("client-payment-status",lambda:validate_request(c,bad)))
    bad=copy.deepcopy(request); bad["card_token"]="redacted-canary"; cases.append(("payment-credential",lambda:validate_request(c,bad)))
    bad=copy.deepcopy(request); bad["hostname"]="acme.example.test"; cases.append(("raw-tenant-coordinate",lambda:validate_request(c,bad)))
    bad=copy.deepcopy(state); bad["events"][0]["signatureVerified"]=False; cases.append(("unsigned-event",lambda:validate_lifecycle(c,bad)))
    bad=copy.deepcopy(state); bad["events"].append(copy.deepcopy(bad["events"][0])); cases.append(("duplicate-event",lambda:validate_lifecycle(c,bad)))
    bad=copy.deepcopy(state); bad["subscription"]["verificationMode"]="browser-callback"; cases.append(("client-trusted-subscription",lambda:validate_lifecycle(c,bad)))
    bad=copy.deepcopy(state); bad.pop("subscription"); cases.append(("active-without-subscription",lambda:validate_lifecycle(c,bad)))
    bad=copy.deepcopy(state); bad["provisioning"]["state"]="pending"; bad["provisioning"].pop("externalRef"); cases.append(("active-before-provisioned",lambda:validate_lifecycle(c,bad)))
    bad=copy.deepcopy(state); bad["provisioning"]["attempts"]=21; cases.append(("unbounded-provisioning",lambda:validate_lifecycle(c,bad)))
    bad=copy.deepcopy(receipt); bad["providerPayload"]={"status":"ACTIVE"}; cases.append(("provider-payload-receipt",lambda:validate_receipt(c,bad)))
    bad=copy.deepcopy(receipt); bad["paymentDataStored"]=True; cases.append(("payment-data-receipt",lambda:validate_receipt(c,bad)))
    rejected=[]
    for name,case in cases:
        try: case()
        except (ContractError,KeyError,TypeError): rejected.append(name)
        else: raise AssertionError(f"adversarial case accepted: {name}")
    return {"schema":"wellmanifest.saas-lifecycle-conformance/v1","ok":True,"schemaDigest":"sha256:"+SCHEMA_DIGEST,"grammarDigest":"sha256:"+GRAMMAR_DIGEST,"positiveVariants":4,"adversarialRejected":rejected}


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--all",action="store_true"); args=p.parse_args()
    if not args.all: p.error("--all is required")
    print(json.dumps(run_all(),indent=2,sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
