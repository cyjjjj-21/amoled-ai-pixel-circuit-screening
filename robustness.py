#!/usr/bin/env python3
"""Parameter-perturbation robustness audit for the preliminary screen."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from screen import BehavioralSimulator, RESULTS, enumerate_timings, enumerate_topologies


SCENARIOS = {
    "baseline": {},
    "switch_2x_slower": {"G_ON": BehavioralSimulator.G_ON / 2},
    "switch_2x_faster": {"G_ON": BehavioralSimulator.G_ON * 2},
    "parasitic_2x": {"C_PAR": BehavioralSimulator.C_PAR * 2, "C_GS": BehavioralSimulator.C_GS * 2},
    "parasitic_half": {"C_PAR": BehavioralSimulator.C_PAR / 2, "C_GS": BehavioralSimulator.C_GS / 2},
    "c1_minus10_c2_plus10": {"C1": 36e-15, "C2": 44e-15},
    "c1_plus10_c2_minus10": {"C1": 44e-15, "C2": 36e-15},
    "mobility_minus20": {"BETA": BehavioralSimulator.BETA * 0.8},
    "mobility_plus20": {"BETA": BehavioralSimulator.BETA * 1.2},
}


def run_scenario(name: str, params: dict, topologies, timings) -> list[dict]:
    rows = []
    for topology in topologies:
        sim = BehavioralSimulator(topology)
        for key, value in params.items():
            setattr(sim, key, value)
        # Rebuild C when a capacitance parameter changes.
        if any(k.startswith("C") for k in params):
            sim.C = np.eye(5) * sim.C_PAR
            sim._add_cap("G", topology.c1_other, sim.C1)
            sim._add_cap("A", "B", sim.C2)
            sim._add_cap("G", "S", sim.C_GS)
            sim.C[4, 4] += sim.C_OLED
        for timing in timings:
            m = sim.run(timing)
            rows.append(
                {
                    "candidate_id": f"{topology.topology_id}+{timing.timing_id}",
                    "topology_id": topology.topology_id,
                    "functional": m["functional"],
                    "score": m["score"],
                    "max_rcer_pct": m["max_rcer_pct"],
                    "address_us": timing.address_us,
                }
            )
    return sorted((r for r in rows if r["functional"]), key=lambda r: -r["score"])


def main() -> None:
    topologies, _ = enumerate_topologies()
    timings = enumerate_timings()
    ranked = {name: run_scenario(name, params, topologies, timings) for name, params in SCENARIOS.items()}
    baseline_top10 = [r["candidate_id"] for r in ranked["baseline"][:10]]
    common = set.intersection(*(set(r["candidate_id"] for r in rows) for rows in ranked.values()))
    rank_maps = {
        name: {r["candidate_id"]: (i + 1, r) for i, r in enumerate(rows)}
        for name, rows in ranked.items()
    }
    robust_rows = []
    for candidate_id in common:
        entries = [rank_maps[name][candidate_id] for name in SCENARIOS]
        ranks = [e[0] for e in entries]
        records = [e[1] for e in entries]
        baseline_record = rank_maps["baseline"][candidate_id][1]
        robust_rows.append(
            {
                "candidate_id": candidate_id,
                "topology_id": baseline_record["topology_id"],
                "mean_rank": float(np.mean(ranks)),
                "worst_rank": int(max(ranks)),
                "best_rank": int(min(ranks)),
                "baseline_score": baseline_record["score"],
                "baseline_proxy_rcer_pct": baseline_record["max_rcer_pct"],
                "worst_proxy_rcer_pct": float(max(r["max_rcer_pct"] for r in records)),
                "address_us": baseline_record["address_us"],
            }
        )
    robust_rows.sort(key=lambda r: (r["mean_rank"], r["worst_rank"], r["worst_proxy_rcer_pct"]))
    audit = {}
    for name, rows in ranked.items():
        rank = {r["candidate_id"]: i + 1 for i, r in enumerate(rows)}
        top10_ranks = [rank.get(c) for c in baseline_top10]
        finite = [x for x in top10_ranks if x is not None]
        audit[name] = {
            "functional_combinations": len(rows),
            "winner": rows[0] if rows else None,
            "winner_topology": rows[0]["topology_id"] if rows else None,
            "top20_topology_counts": dict(Counter(r["topology_id"] for r in rows[:20])),
            "baseline_top10_retained_in_top20": sum(1 for x in finite if x <= 20),
            "baseline_top10_median_rank": float(np.median(finite)) if finite else None,
        }
    result = {
        "scenarios": SCENARIOS,
        "baseline_top10": baseline_top10,
        "audit": audit,
        "all_scenarios_same_winner_topology": len({v["winner_topology"] for v in audit.values()}) == 1,
        "functional_in_all_scenarios": len(common),
        "robust_top10": robust_rows[:10],
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "robustness.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (RESULTS / "final_top10.json").write_text(
        json.dumps(robust_rows[:10], indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
