"""Independent bounded oracle data for SAE-60 qualification tests.

This module deliberately does not import the production candidate analyzer and
does not parse source. Expected relations are separately authored and bound to
an exact source digest so candidate logic cannot define its own ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib


ORACLE_IMPLEMENTATION_LINEAGE_ID = hashlib.sha256(
    b"sae60-independent-manual-bounded-oracle-v1"
).hexdigest()


@dataclass(frozen=True)
class OracleRelation:
    table: str
    key: str
    target: str


@dataclass(frozen=True)
class OracleFixture:
    fixture_id: str
    source: str
    source_sha256: str
    expected: tuple[OracleRelation, ...]


def _fixture(fixture_id: str, source: str, expected: tuple[tuple[str, str, str], ...]) -> OracleFixture:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return OracleFixture(
        fixture_id,
        source,
        digest,
        tuple(OracleRelation(*relation) for relation in expected),
    )


TRAINING_FIXTURE = _fixture(
    "command-router-training-v1",
    '''def scan():
    return "scan"

def evidence():
    return "evidence"

def review():
    return "review"

def final_gate():
    return "final"

COMMANDS = {
    "scan": scan,
    "evidence": evidence,
    "review": review,
    "final": final_gate,
}

def startup_checks():
    COMMANDS["scan"]()
    COMMANDS["evidence"]()
    COMMANDS["review"]()
    COMMANDS["final"]()
''',
    (
        ("COMMANDS", "scan", "scan"),
        ("COMMANDS", "evidence", "evidence"),
        ("COMMANDS", "review", "review"),
        ("COMMANDS", "final", "final_gate"),
    ),
)


HOLDOUT_FIXTURE = _fixture(
    "release-router-hidden-holdout-v1",
    '''def package():
    return "package"

def sign():
    return "sign"

def publish():
    return "publish"

def verify():
    return "verify"

def release_pipeline():
    RELEASE_STEPS["package"]()
    RELEASE_STEPS["sign"]()
    RELEASE_STEPS["publish"]()
    RELEASE_STEPS["verify"]()

RELEASE_STEPS = {
    "package": package,
    "sign": sign,
    "publish": publish,
    "verify": verify,
}
''',
    (
        ("RELEASE_STEPS", "package", "package"),
        ("RELEASE_STEPS", "sign", "sign"),
        ("RELEASE_STEPS", "publish", "publish"),
        ("RELEASE_STEPS", "verify", "verify"),
    ),
)


TRANSFER_FIXTURE = _fixture(
    "incident-router-transfer-v1",
    '''def collect_logs():
    return "logs"

def isolate_host():
    return "isolate"

def restore_service():
    return "restore"

def incident_playbook():
    ACTION_MATRIX["collect"]()
    ACTION_MATRIX["isolate"]()
    ACTION_MATRIX["restore"]()

ACTION_MATRIX = {
    "collect": collect_logs,
    "isolate": isolate_host,
    "restore": restore_service,
}
''',
    (
        ("ACTION_MATRIX", "collect", "collect_logs"),
        ("ACTION_MATRIX", "isolate", "isolate_host"),
        ("ACTION_MATRIX", "restore", "restore_service"),
    ),
)


def expected_relations(fixture: OracleFixture) -> tuple[tuple[str, str, str], ...]:
    if hashlib.sha256(fixture.source.encode("utf-8")).hexdigest() != fixture.source_sha256:
        raise AssertionError("oracle fixture source no longer matches its frozen digest")
    return tuple((item.table, item.key, item.target) for item in fixture.expected)


def exact_match(fixture: OracleFixture, observed: tuple[tuple[str, str, str], ...]) -> bool:
    return observed == expected_relations(fixture)
