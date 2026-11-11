"""Core contract primitives, strict loaders, and schema/DSL pin checks for SaaS lifecycle v1."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import lifecycle

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "saas-lifecycle.schema.json"
GRAMMAR_PATH = ROOT / "saas-lifecycle.v1.gbnf"
PROFILE_SCHEMA_PATH = ROOT / "saas-adapter-profile.schema.json"
PROFILE_EXAMPLES_PATH = ROOT / "adapter-profiles.examples.json"
LIFECYCLE_PATH = ROOT / "saas-lifecycle.lifecycle"
LIFECYCLE_VALIDATOR_PATH = ROOT / "lifecycle.py"

SCHEMA_DIGEST = "f53aef1a48c3f8e20190a49e1b16438cafdb602b2744684d249d71798802a7b2"
GRAMMAR_DIGEST = "2565b1c0e93c1f5ee84c299428ef8592e295b4a3337585409ae1ee19644d7690"
PROFILE_SCHEMA_DIGEST = "060495e3dda6a80bc67d861d55422dff65df912028b0d3a7a598959de3df7054"
PROFILE_EXAMPLES_DIGEST = "5ed1f16934de26008feafdcdd98577298db2474c8ddf8b5aa0128aadfb52fc49"
LIFECYCLE_SOURCE_REVISION = "1ea2a90bd5b90a768ad2b36a9c1c330523bc80b4"
LIFECYCLE_VALIDATOR_DIGEST = "7f7f1c45b7611e186cc640ada69cf2849d16841564c4028b9fc06dd0a05c2b3a"
LIFECYCLE_PROFILE_DIGEST = "e95791ea1d8d9e38c494ba38ca8abbdf2eba6816a122850d76359c6d356e9ed0"
SCHEMA_URI = "https://wellmanifest.dev/schemas/saas-lifecycle/v1"
PROFILE_SCHEMA_URI = "https://wellmanifest.dev/schemas/saas-adapter-profile/v1"

SENSITIVE = re.compile(
    r"(?:password|passwd|token|secret|cookie|api[-_]?key|card|cvv|"
    r"private[-_]?key|webhook[-_]?signature)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~+/-]{16,}|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)
SAFE_ASSERTIONS = {"secretsRedacted", "paymentDataStored", "signatureVerified"}
UNSAFE_POINTER_SEGMENT = re.compile(
    r"(?:password|passwd|token|secret|cookie|api[-_]?key|card|cvv|private[-_]?key|"
    r"webhook[-_]?signature|host(?:name)?|user(?:name)?|docroot|domain|source[-_]?dir|"
    r"vault[-_]?url|base[-_]?url)",
    re.IGNORECASE,
)
LIFECYCLE_TRANSITIONS = {
    ("REQUESTED", "MEMBERSHIP_VERIFIED", "SIGNUP"),
    ("MEMBERSHIP_VERIFIED", "TRIAL_ACTIVE", "START_TRIAL"),
    ("MEMBERSHIP_VERIFIED", "PAYMENT_PENDING", "SELECT_PLAN"),
    ("TRIAL_ACTIVE", "TRIAL_EXPIRING", "TRIAL_NOTICE"),
    ("TRIAL_ACTIVE", "CANCELLED", "CANCEL"),
    ("TRIAL_EXPIRING", "PAYMENT_PENDING", "SELECT_PLAN"),
    ("TRIAL_EXPIRING", "EXPIRED", "EXPIRE"),
    ("PAYMENT_PENDING", "PAID_PENDING_PROVISIONING", "CONFIRM_SUBSCRIPTION"),
    ("PAID_PENDING_PROVISIONING", "ACTIVE", "PROVISION"),
    ("PAID_PENDING_PROVISIONING", "FAILED", "FAIL"),
    ("ACTIVE", "ACTIVE", "PURCHASE_ADDON"),
    ("ACTIVE", "PLAN_CHANGE_PENDING", "REQUEST_PLAN_CHANGE"),
    ("PLAN_CHANGE_PENDING", "ACTIVE", "ACTIVATE_PLAN_CHANGE"),
    ("ACTIVE", "SUSPENDED", "SUSPEND"),
    ("ACTIVE", "CANCELLED", "CANCEL"),
    ("SUSPENDED", "ACTIVE", "RESUME"),
    ("SUSPENDED", "EXPIRED", "EXPIRE"),
}
REF_NAMES = (
    "identifier", "sha256", "sha256Ref", "accountRef", "tenantRef", "planRef", "priceRef",
    "providerRef", "billingRef", "intentRef", "grantRef", "eventRef", "evidenceRef",
    "outboxRef", "deploymentRef", "entitlementRef", "metricRef", "organizationRef",
    "projectRef", "ticketRef", "processRunRef", "attemptRef", "principalRef",
    "uriProcessRef", "operationClassRef", "meteringRuleRef", "usageEntryRef",
    "authorityGrantRef", "leaseRef", "currency",
)


class ContractError(ValueError):
    """A bounded error that never repeats untrusted provider data."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def reject_no_symlink(path: Path) -> None:
    cur = Path(path.anchor) if path.is_absolute() else Path()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        cur = cur / part
        if cur.is_symlink():
            raise ContractError("symlinked contract artifact is forbidden")


def file_digest(path: Path) -> str:
    reject_no_symlink(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json_load(path: Path) -> Any:
    reject_no_symlink(path)

    def _no_dups(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, val in pairs:
            if key in out:
                raise ContractError("duplicate JSON key in contract")
            out[key] = val
        return out

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_dups)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError("contract JSON is unreadable") from error


def is_int(value: Any) -> bool:
    return type(value) is int


def unique_str_list(
    value: Any, *, min_items: int = 1, max_items: int = 1024, label: str = "list"
) -> list[str]:
    if not isinstance(value, list) or not (min_items <= len(value) <= max_items):
        raise ContractError(f"invalid {label}")
    if not all(isinstance(item, str) and bool(item.strip()) for item in value):
        raise ContractError(f"invalid {label}")
    if len(value) != len(set(value)):
        raise ContractError(f"duplicate {label}")
    return value


def lifecycle_name(value: str) -> str:
    return value.upper().replace("-", "_")


def validate_lifecycle_profile(schema: dict[str, Any]) -> None:
    if file_digest(LIFECYCLE_VALIDATOR_PATH) != LIFECYCLE_VALIDATOR_DIGEST:
        raise ContractError("pinned lifecycle validator digest mismatch")
    if file_digest(LIFECYCLE_PATH) != LIFECYCLE_PROFILE_DIGEST:
        raise ContractError("pinned lifecycle profile digest mismatch")
    report = lifecycle.validate_path(LIFECYCLE_PATH, lifecycle.embedded_catalog())
    if not report.valid or len(report.lifecycles) != 1:
        raise ContractError("Lifecycle DSL profile is invalid")
    if lifecycle.audit_path(LIFECYCLE_PATH)["finding_count"] != 0:
        raise ContractError("Lifecycle DSL profile has compaction findings")
    model = report.lifecycles[0]
    state_values = schema["$defs"]["lifecycle"]["properties"]["state"]["enum"]
    expected_states = {lifecycle_name(str(value)) for value in state_values}
    actual_transitions = {(item.source, item.target, item.event) for item in model.transitions}
    if model.name != "saas-tenant" or set(model.states) != expected_states:
        raise ContractError("Lifecycle DSL state graph mismatch")
    if actual_transitions != LIFECYCLE_TRANSITIONS:
        raise ContractError("Lifecycle DSL transition graph mismatch")
    if model.summary()["initial_state"] != "REQUESTED":
        raise ContractError("Lifecycle DSL initial state mismatch")
    if model.summary()["terminal_states"] != ["CANCELLED", "EXPIRED", "FAILED"]:
        raise ContractError("Lifecycle DSL terminal state mismatch")


def exact(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("expected object")
    optional = optional or set()
    if set(value) - required - optional:
        raise ContractError("undeclared field")
    if required - set(value):
        raise ContractError("missing field")
    return value


def time_value(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ContractError("invalid date-time")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ContractError("invalid date-time") from error
    if result.tzinfo is None:
        raise ContractError("timezone required")
    return result


def reject_sensitive(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or (SENSITIVE.search(key) and key not in SAFE_ASSERTIONS):
                raise ContractError("sensitive data channel")
            reject_sensitive(child)
    elif isinstance(value, list):
        for child in value:
            reject_sensitive(child)
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise ContractError("sensitive secret value")


class Contracts:
    def __init__(self) -> None:
        reject_no_symlink(GRAMMAR_PATH)
        self.schema = strict_json_load(SCHEMA_PATH)
        self.grammar = GRAMMAR_PATH.read_text(encoding="utf-8")
        self.profile_schema = strict_json_load(PROFILE_SCHEMA_PATH)
        self.profile_examples = strict_json_load(PROFILE_EXAMPLES_PATH)
        defs = self.schema.get("$defs", {})
        self.patterns = {name: re.compile(defs[name]["pattern"]) for name in REF_NAMES}
        self.max_lengths = {
            name: int(defs[name]["maxLength"])
            for name in REF_NAMES
            if "maxLength" in defs[name]
        }

    def ref(self, name: str, value: Any) -> str:
        max_len = self.max_lengths.get(name)
        if (
            not isinstance(value, str)
            or (max_len is not None and len(value) > max_len)
            or self.patterns[name].fullmatch(value) is None
        ):
            raise ContractError(f"invalid {name}")
        return value

    def integrity(self) -> None:
        draft = "https://json-schema.org/draft/2020-12/schema"
        if self.schema.get("$schema") != draft or self.schema.get("$id") != SCHEMA_URI:
            raise ContractError("schema identity mismatch")
        if digest(canonical(self.schema)) != SCHEMA_DIGEST or digest(self.grammar) != GRAMMAR_DIGEST:
            raise ContractError("contract digest mismatch")
        if (
            self.profile_schema.get("$schema") != draft
            or self.profile_schema.get("$id") != PROFILE_SCHEMA_URI
        ):
            raise ContractError("profile schema identity mismatch")
        if (
            digest(canonical(self.profile_schema)) != PROFILE_SCHEMA_DIGEST
            or digest(canonical(self.profile_examples)) != PROFILE_EXAMPLES_DIGEST
        ):
            raise ContractError("profile contract digest mismatch")
        expected_variants = {
            "#/$defs/offer",
            "#/$defs/request",
            "#/$defs/lifecycle",
            "#/$defs/receipt",
            "#/$defs/usageLedgerEntry",
        }
        if {x.get("$ref") for x in self.schema.get("oneOf", [])} != expected_variants:
            raise ContractError("document variants incomplete")
        if {x.get("$ref") for x in self.profile_schema.get("oneOf", [])} != {
            "#/$defs/paymentProfile",
            "#/$defs/deploymentProfile",
        }:
            raise ContractError("profile variants incomplete")
        if self.profile_examples.get("schema") != "wellmanifest.saas-adapter-profile-examples/v1":
            raise ContractError("profile examples identity mismatch")
        for fragment in (
            "root ::= request",
            "payment status",
            "purchase_addon",
            "plan-ref ::=",
            "price-ref ::=",
            "billing-ref ::=",
            "sha256 ::=",
        ):
            if fragment not in self.grammar:
                raise ContractError("grammar incomplete")
        self._closed(self.schema)
        self._closed(self.profile_schema)

    def _closed(self, value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object" and value.get("additionalProperties") is not False:
                raise ContractError("open object schema")
            for child in value.values():
                self._closed(child)
        elif isinstance(value, list):
            for child in value:
                self._closed(child)
