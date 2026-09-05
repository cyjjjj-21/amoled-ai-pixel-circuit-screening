"""Read-only integrity checks for the delivered finite screening evidence."""
import csv
import json
import math
from pathlib import Path
import re


def main():
    out = Path(__file__).resolve().parents[1] / "results_v3"
    tables = {}
    for name, count in {
        "structure_audit": 3024, "all_candidates": 180, "dynamic_candidates": 55296,
        "timings": 24, "top10": 10, "spice_validation": 90,
    }.items():
        with (out / f"{name}.csv").open() as handle:
            tables[name] = list(csv.DictReader(handle))
        assert len(tables[name]) == count, (name, len(tables[name]))
        for row in tables[name]:
            for field, value in row.items():
                try:
                    numeric = float(value)
                except (ValueError, TypeError):
                    continue
                assert math.isfinite(numeric), (name, field, value)
    passed = [r for r in tables["structure_audit"] if r["decision"] == "ideal_mechanism_pass"]
    assert len(passed) == 5
    for row in passed:
        structure = json.loads((out / f"{row['structure_id']}.json").read_text())
        assert len(structure["caps"]) <= 2 and structure["groups"] <= 5
    summary = json.loads((out / "summary.json").read_text())
    assert summary["global_optimum_certified"] is False and summary["PDK_simulations"] == 0
    top = tables["top10"]
    assert len({(r["c1_ff"], r["c2_ff"]) for r in top}) == 10
    assert [r["candidate_id"] for r in top] == [r["candidate_id"] for r in summary["top10"]]
    valid_timings = {r["timing_id"] for r in tables["timings"]}
    for row in tables["spice_validation"]:
        rank = int(row["rank"])
        assert row["parameter_id"] == top[rank-1]["candidate_id"]
        assert row["timing_id"] == top[rank-1]["reference_timing"]
        assert row["timing_id"] in valid_timings
        netlist = out / "spice" / row["netlist"]
        assert netlist.is_file()
        log = netlist.with_suffix(".log").read_text()
        assert not re.search(r"\b(error|warning|failed)\b", log, re.I), netlist.name
        for key in ("overdrive", "vgs_comp", "vgs_end", "source_before", "source_after"):
            match = re.search(rf"^\s*{key}\s*=\s*([-+\d.eE]+)", log, re.M)
            assert match and float(match[1]) == float(row[key]), (netlist.name, key)
    report = (out / "REPORT.md").read_text()
    for target in re.findall(r"\]\(([^)]+)\)", report):
        if not target.startswith(("http:", "https:", "#")):
            assert (out / target).exists(), target
    print("Integrity passed: 3024 structures, 180 parameters, 24 timings, 55296 dynamic rows, 90 SPICE logs.")


if __name__ == "__main__":
    main()
