"""The provable 'it works' artifact.

Runs the whole scan over the synthetic environment and checks it against the
embedded answer key: every planted zombie must be caught (recall) and nothing
healthy or brand-new may be flagged (precision). Prints a precision/recall
summary so the result is visible in the test output.
"""

from __future__ import annotations

import json
from pathlib import Path

from gravekeeper.connectors.synthetic import SyntheticConnector
from gravekeeper.pipeline import run_scan

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_env.json"


def _ground_truth() -> dict[str, dict]:
    data = json.loads(FIXTURE.read_text())
    return {
        item["id"]: {
            "expected_zombie": item["expected_zombie"],
            "expected_reasons": set(item.get("expected_reasons", [])),
        }
        for item in data["identities"]
    }


def test_synthetic_pipeline_precision_and_recall(capsys):
    connector = SyntheticConnector()
    result = run_scan(connector, now=connector.reference_now)
    truth = _ground_truth()

    findings = {f.agent_id: f for f in result.findings}
    assert set(findings) == set(truth), "every identity should be scored"

    tp = fp = fn = tn = 0
    reason_mismatches: list[str] = []

    for agent_id, expected in truth.items():
        f = findings[agent_id]
        predicted = f.is_zombie_candidate
        actual = expected["expected_zombie"]

        if predicted and actual:
            tp += 1
            got = {r.value for r in f.reasons}
            if got != expected["expected_reasons"]:
                reason_mismatches.append(
                    f"{agent_id}: expected "
                    f"{sorted(expected['expected_reasons'])}, got {sorted(got)}"
                )
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    with capsys.disabled():
        print("\n--- synthetic environment scan ---")
        print(f"identities scanned : {result.total_identities}")
        print(f"planted zombies    : {tp + fn}")
        print(f"caught (TP)        : {tp}")
        print(f"missed (FN)        : {fn}")
        print(f"false alarms (FP)  : {fp}")
        print(f"correct healthy    : {tn}")
        print(f"precision          : {precision:.2%}")
        print(f"recall             : {recall:.2%}")
        print("----------------------------------")

    assert fn == 0, "missed a planted zombie (recall < 100%)"
    assert fp == 0, "flagged a healthy/new identity (false positive)"
    assert recall == 1.0
    assert precision == 1.0
    assert not reason_mismatches, "reason mismatches:\n" + "\n".join(reason_mismatches)


def test_scan_result_shape():
    connector = SyntheticConnector()
    result = run_scan(connector, now=connector.reference_now)
    assert result.total_identities == 30
    assert result.zombie_candidates == 16
    assert result.environment_label.startswith("northwind-labs")
    assert len(result.records) == result.total_identities
