#!/usr/bin/env python3
"""Constraint-faithful, charge-conserving finite pixel-circuit audit.

No process-qualified IGZO model is bundled. This program evaluates ideal switched
capacitor mechanisms, explicit parasitic scenarios, and declared timing proxies.
It does not claim arbitrary-graph completeness or PDK-qualified Top 10 designs.
"""
from __future__ import annotations

import csv
import hashlib
import itertools as it
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from proxy_models import TECH

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results_v3"
NODES = ("G", "S", "X")
EDGES = tuple(it.combinations((*NODES, "R"), 2))
EPS = 1e-7  # numerical identity tolerance, not an electrical specification
USER_CONSTRAINTS = [
    "DTFT 为 IGZO TFT；电容最多 2 个；GOA 控制信号最多 5 组；STFT 可用 LTPS 或 IGZO",
    "DATA 电压变化写入 DTFT Vgs 时有压缩比",
    "阈值电压补偿与 DATA 写入分离",
    "DATA 写入后 Vgs 保持相对稳定；源极变化时优先使 Vgs 稳定性最好",
]


@dataclass(frozen=True)
class Structure:
    caps: tuple[tuple[str, str], ...]
    anchor: str
    track_prep: bool
    data_node: str
    anchor_emit: bool
    split_source: bool
    isolate_drain: bool

    @property
    def sid(self):
        return "S3-" + hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:10]

    def switches(self):
        # ON masks: RESET, COMP, PREP, WRITE, EMIT. Logic 1 means conduction,
        # not necessarily a high gate voltage. PWR is p-LTPS with complement mask.
        switches = [
            ("GREF", "G", "VREF", "11000", "n"),
            ("XANCHOR", "X", {"R": "VREF", "S": "S", "G": "G"}[self.anchor],
             "11" + ("1" if self.track_prep else "0") + "0" + ("1" if self.anchor_emit else "0"), "n"),
            ("DATA", self.data_node, "VDATA", "00010", "n"),
            ("EM", "S", "OLED_A", "00001", "n"),
        ]
        if self.split_source:
            switches.extend([("SRESET", "S", "VINIT", "10000", "n"),
                             ("SHOLD", "S", "VINIT", "00110", "n")])
        else:
            switches.append(("SCLAMP", "S", "VINIT", "10110", "n"))
        if self.isolate_drain:
            switches.append(("PWR", "VDD", "D", "01001", "p"))
        return switches

    @property
    def groups(self):
        return len({mask if polarity == "n" else "".join("1" if x == "0" else "0" for x in mask)
                    for _, _, _, mask, polarity in self.switches()})


def structures():
    cap_sets = [(e,) for e in EDGES] + list(it.combinations(EDGES, 2))
    for caps, anchor, prep, data, emit, split, isolation in it.product(
        cap_sets, ("R", "S", "G"), (False, True), NODES,
        (False, True), (False, True), (False, True)
    ):
        yield Structure(caps, anchor, prep, data, emit, split, isolation)


def capacitance(caps, values, parasitic=(0.0, 0.0, 0.0)):
    matrix = np.diag(np.asarray(parasitic, dtype=float))
    for (a, b), value in zip(caps, values):
        vector = np.array([float(n == a) - float(n == b) for n in NODES])
        matrix += value * np.outer(vector, vector)
    return matrix


def constraints(fixed, anchor=None):
    vectors, targets = [], []
    for node, value in fixed.items():
        vectors.append([float(n == node) for n in NODES])
        targets.append(value)
    if anchor is not None:
        vector = [float(n == "X") - float(n == anchor) for n in NODES]
        vectors.append(vector)
        targets.append(np.array([3., 0., 0.]) if anchor == "R" else np.zeros(3))
    return np.asarray(vectors), np.asarray(targets)


def transition(matrix, previous, fixed, anchor=None):
    """KKT charge projection; columns are constant, VTH and DATA coefficients.

    C(v_new-v_old)=A.T*q and A*v_new=b conserve total charge on every
    floating conductor (including shorted groups). Null nodes remain at their
    previous voltage; only observable voltages affect mechanism acceptance.
    """
    matrix = matrix / max(float(np.max(np.abs(matrix))), 1.)
    a, b = constraints(fixed, anchor)
    if not len(a):
        return previous.copy()
    kkt = np.block([[matrix, a.T], [a, np.zeros((len(a), len(a)))]])
    rhs = np.vstack([np.zeros_like(previous), b - a @ previous])
    delta = np.linalg.lstsq(kkt, rhs, rcond=1e-12)[0][:3]
    result = previous + delta
    if np.max(np.abs(a @ result - b)) > 1e-6:
        raise ValueError("conflicting_voltage_constraints")
    return result


def transfer(s, values, parasitic=(0., 0., 0.)):
    c = capacitance(s.caps, values, parasitic)
    vref = np.array([3., 0., 0.])
    vinit = np.array([0., 0., 0.])
    # Favorable full-settling source-follower assumption. Dynamic settling must
    # be evaluated separately and is not implied by this identity test.
    comp = transition(c, np.zeros((3, 3)), {"G": vref, "S": np.array([3., -1., 0.])}, s.anchor)
    prep = transition(c, comp, {"S": vinit}, s.anchor if s.track_prep else None)
    if s.data_node == "S":
        raise ValueError("DATA_and_VINIT_short_in_WRITE")
    write = transition(c, prep, {"S": vinit, s.data_node: np.array([0., 0., 1.])})
    emit = transition(c, write, {"S": np.array([1., 0., 0.])}, s.anchor if s.anchor_emit else None)
    emit2 = transition(c, write, {"S": np.array([2., 0., 0.])}, s.anchor if s.anchor_emit else None)
    vgs = emit[0] - emit[1]
    return {
        "kappa": float(vgs[2]),
        "write_kappa": float((write[0] - write[1])[2]),
        "vth_residual": float(vgs[1] - 1.),
        "source_sensitivity": float((emit2[0] - emit2[1] - vgs)[0]),
        "offset_v": float(vgs[0]),
        "stages": {name: v.tolist() for name, v in (("COMP", comp), ("PREP", prep), ("WRITE", write), ("EMIT", emit))},
    }


def audit(s):
    row = {"structure_id": s.sid, "caps": ";".join("-".join(e) for e in s.caps),
           "anchor": s.anchor, "track_prep": s.track_prep, "data_node": s.data_node,
           "anchor_emit": s.anchor_emit, "split_source": s.split_source,
           "isolate_drain": s.isolate_drain, "control_groups": s.groups,
           "transistors": 1 + len(s.switches())}
    if s.groups > 5:
        return row | {"decision": "control_groups_gt_5"}
    try:
        results = [transfer(s, [100.] if len(s.caps) == 1 else [100., b]) for b in (30., 100., 230.)]
    except ValueError as error:
        return row | {"decision": str(error)}
    row.update({k: results[0][k] for k in ("kappa", "vth_residual", "source_sensitivity")})
    if any(not EPS < abs(r["kappa"]) < 1 - EPS for r in results):
        return row | {"decision": "no_intrinsic_DATA_compression"}
    if any(not EPS < abs(r["write_kappa"]) < 1 - EPS for r in results):
        return row | {"decision": "compression_only_after_WRITE"}
    if any(abs(r["vth_residual"]) > EPS for r in results):
        return row | {"decision": "VTH_lost_across_phases"}
    # User requests best source stability, so there is no arbitrary 5% cutoff.
    return row | {"decision": "ideal_mechanism_pass"}


def dump_csv(path, rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def scan_parameters(survivors):
    # Finite numerical domain, not user limits. Boundary extension is measured.
    cap_values = (20., 40., 80., 160., 320., 640.)
    rows = []
    for s in survivors:
        for values in it.product(cap_values, repeat=len(s.caps)):
            ideal = transfer(s, values)
            measured = transfer(s, values, (3., 20., 2.))
            key = json.dumps([s.sid, values])
            rows.append({"candidate_id": "P3-" + hashlib.sha256(key.encode()).hexdigest()[:10],
                         "structure_id": s.sid, "c1_ff": values[0], "c2_ff": values[1],
                         "kappa": measured["kappa"], "abs_vth_residual": abs(measured["vth_residual"]),
                         "source_sensitivity": abs(measured["source_sensitivity"]),
                         "ideal_vth_residual": ideal["vth_residual"],
                         "total_cap_ff": sum(values), "transistors": 1 + len(s.switches()),
                         "control_groups": s.groups, "isolate_drain": s.isolate_drain})
    return rows


def rank_and_front(rows):
    # Only optimize user's stability priority. Tie-breakers are disclosed display
    # conventions, not a fabricated weighted performance objective.
    rows.sort(key=lambda r: (round(r["source_sensitivity"], 10), round(r["abs_vth_residual"], 10),
                             r["total_cap_ff"], r["transistors"], r["control_groups"], r["candidate_id"]))
    fields = ("source_sensitivity", "abs_vth_residual", "total_cap_ff", "transistors")
    for row in rows:
        row["pareto"] = not any(
            all(other[f] <= row[f] + 1e-12 for f in fields)
            and any(other[f] < row[f] - 1e-12 for f in fields)
            for other in rows
        )
    # Unique electrical cap networks for Top 10; preserve drain-isolated variants
    # separately rather than inflating the list with electrically tied designs.
    unique, seen = [], set()
    for row in rows:
        key = (row["c1_ff"], row["c2_ff"], round(row["kappa"], 8),
               round(row["source_sensitivity"], 8))
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique[:10]


def timing_sweep():
    # No pass/fail timing threshold without a line-time or error specification.
    rows = []
    for comp, write, dead in it.product((2., 8., 32., 128.), (.05, .2, 1.), (.02, .1)):
        rows.append({"timing_id": f"T3-{len(rows)+1:02}", "reset_us": .5,
                     "comp_us": comp, "prep_us": .2, "write_us": write,
                     "break_comp_prep_us": dead, "break_prep_write_us": dead,
                     "break_write_emit_us": dead, "address_us": .7 + comp + write + 3 * dead})
    return rows


def charge_history(s, row):
    result = transfer(s, (row["c1_ff"], row["c2_ff"]), (3., 20., 2.))
    return [{"stage": stage, "node": node, "constant": values[i][0],
             "vth_coefficient": values[i][1], "data_coefficient": values[i][2]}
            for stage, values in result["stages"].items() for i, node in enumerate(NODES)]


def rc_decay(cap, conductance, duration):
    """Real passive RC evolution via a symmetric energy-coordinate transform."""
    lower = np.linalg.cholesky(cap)
    inverse = np.linalg.solve(lower, np.eye(len(cap)))
    symmetric = inverse @ conductance @ inverse.T
    eig, vec = np.linalg.eigh((symmetric + symmetric.T) / 2.)
    return inverse.T @ (vec @ np.diag(np.exp(-eig * duration)) @ vec.T) @ lower.T


def dynamic_metrics(row, timing, techs, beta_uav2=1.):
    """Explicit reduced-order electrical scenario; not a PDK transient solve.

    Source-follower sampling uses I=beta/2*(VGS-VTH)^2 and its exact ODE
    solution. DATA/prep use single-pole RC. During hold, the coupled G/X
    capacitance matrix and all three storage leakage conductances are solved
    together by a matrix exponential. Source and reference rails stay prescribed.
    """
    cst, cd = row["c1_ff"], row["c2_ff"]
    cg, cx, cs = 3., 2., 20.
    kappa = row["kappa"]
    a = 1. - row["abs_vth_residual"]
    comp_c_ff = cst + cd + cx + cs  # G clamped; X shorted to S during COMP
    beta = beta_uav2 * 1e-6
    # Source-follower initial overdrive at VREF=3,VINIT=0,VTH=1.
    u0 = 2.
    comp_error = u0 / (1. + beta * u0 * timing["comp_us"] * 1e-6 / (2. * comp_c_ff * 1e-15))
    ceff_data = cx + cd * (cst + cg) / (cst + cd + cg)
    tau_write_us = TECH[techs[2]]["ron_ohm"] * ceff_data * 1e-9
    data_unsettled = np.exp(-timing["write_us"] / tau_write_us)
    # Conservatively use the full source-node capacitance for prep RC diagnostic.
    prep_unsettled = np.exp(-timing["prep_us"] / (TECH[techs[3]]["ron_ohm"] * comp_c_ff * 1e-9))
    gref, xanchor, data = [TECH[t]["goff_s"] for t in techs[:3]]
    cap = np.array([[cst + cd + cg, -cd], [-cd, cd + cx]]) * 1e-15
    conductance = np.diag([gref, xanchor + data])
    # Fixed source=1, reference=3, next-row DATA=0 in this hold scenario.
    equilibrium = np.array([3., xanchor / (xanchor + data)])
    decay = rc_decay(cap, conductance, 1. / 60.)
    s = Structure((("G", "S"), ("G", "X")), "S", row["track_prep"], "X", False, False, False)
    coeffs = transfer(s, (cst, cd), (cg, cs, cx))["stages"]["EMIT"]
    vth = 1. + comp_error
    dvalue = 1.5 * (1. - data_unsettled)
    volts = np.array(coeffs) @ np.array([1., vth, dvalue])
    initial = volts[[0, 2]]
    final = equilibrium + decay @ (initial - equilibrium)
    drift = float(final[0] - initial[0])
    # Error against exact compensated target: VGS=VTH+kappa*VDATA.
    overdrive_error = float(volts[0] - 1. - 1. - kappa * 1.5)
    return {"comp_overdrive_residual_mv": comp_error * 1000.,
            "program_error_mv": overdrive_error * 1000.,
            "hold_delta_vgs_mv": drift * 1000.,
            "write_unsettled_fraction": float(data_unsettled),
            "prep_unsettled_fraction": float(prep_unsettled),
            "em_drop_300na_mv": TECH[techs[4]]["ron_ohm"] * 300e-9 * 1000.,
            "beta_uav2": beta_uav2,
            "sampling_vth_coefficient": a}


def evaluate_dynamics(rows, timing):
    output = []
    # Core six-T candidates: all five n-channel SWT role assignments are allowed.
    # Split-source/drain-isolated variants retain structural audit status and are
    # not silently credited with the same parasitic or leakage performance.
    core = [r for r in rows if r["transistors"] == 6]
    for row in core:
        for techs in it.product(("IGZO", "LTPS"), repeat=5):
            for t in timing:
                metrics = dynamic_metrics(row, t, techs)
                output.append({"parameter_id": row["candidate_id"], "timing_id": t["timing_id"],
                               "switch_mix": "/".join(techs), **metrics})
    return output


def main():
    OUT.mkdir(exist_ok=True)
    all_structures = list(structures())
    audit_rows = [audit(s) for s in all_structures]
    passed = {r["structure_id"] for r in audit_rows if r["decision"] == "ideal_mechanism_pass"}
    survivors = [s for s in all_structures if s.sid in passed]
    rows = scan_parameters(survivors)
    structure_map = {s.sid: s for s in survivors}
    for row in rows:
        row["track_prep"] = structure_map[row["structure_id"]].track_prep
    if not rows:
        raise RuntimeError("No mechanism passed; report infeasibility rather than synthesize winners")
    top10 = rank_and_front(rows)
    timing = timing_sweep()
    dynamic_rows = evaluate_dynamics(rows, timing)
    dump_csv(OUT / "dynamic_candidates.csv", dynamic_rows)
    # Per-cap reference timing: minimum absolute programming error, then hold
    # drift, then emission drop; these are declared presentation priorities.
    by_parameter = {}
    tmap = {t["timing_id"]: t for t in timing}
    for d in dynamic_rows:
        key = d["parameter_id"]
        score = (round(abs(d["program_error_mv"]), 8), abs(d["hold_delta_vgs_mv"]),
                 d["em_drop_300na_mv"], tmap[d["timing_id"]]["address_us"], d["switch_mix"])
        if key not in by_parameter or score < by_parameter[key][0]:
            by_parameter[key] = (score, d)
    for row in top10:
        row.update({"reference_timing": by_parameter[row["candidate_id"]][1]["timing_id"],
                    "reference_mix": by_parameter[row["candidate_id"]][1]["switch_mix"],
                    "program_error_mv": by_parameter[row["candidate_id"]][1]["program_error_mv"],
                    "hold_delta_vgs_mv": by_parameter[row["candidate_id"]][1]["hold_delta_vgs_mv"]})
    dump_csv(OUT / "structure_audit.csv", audit_rows)
    dump_csv(OUT / "all_candidates.csv", rows)
    dump_csv(OUT / "timings.csv", timing)
    dump_csv(OUT / "top10.csv", top10)
    for s in survivors:
        (OUT / f"{s.sid}.json").write_text(json.dumps(asdict(s) | {"switches": s.switches(), "groups": s.groups}, indent=2))
    winner = next(s for s in survivors if s.sid == top10[0]["structure_id"])
    dump_csv(OUT / "charge_history.csv", charge_history(winner, top10[0]))
    old = Structure((("G", "S"), ("G", "X")), "R", False, "X", False, False, False)
    old_audit = transfer(old, (160., 80.))
    extensions = []
    for scale in (1., 2., 4., 8.):
        result = transfer(winner, (top10[0]["c1_ff"]*scale, top10[0]["c2_ff"]*scale), (3., 20., 2.))
        extensions.append({"scale": scale, "total_cap_ff": top10[0]["total_cap_ff"]*scale,
                           **{k: result[k] for k in ("kappa", "vth_residual", "source_sensitivity")}})
    dump_csv(OUT / "boundary_extension.csv", extensions)
    summary = {"version": 3, "user_constraints": USER_CONSTRAINTS,
               "model": "ideal affine charge conservation plus explicit parasitic scenarios",
               "structural_candidates": len(all_structures), "decisions": dict(Counter(r["decision"] for r in audit_rows)),
               "surviving_structures": len(survivors), "parameter_candidates": len(rows),
               "timing_candidates": len(timing), "top10": top10,
               "dynamic_combinations": len(dynamic_rows),
               "old_v2_ideal_transfer": old_audit, "boundary_extension": extensions,
               "global_optimum_certified": False, "PDK_simulations": 0,
               "finite_scope": "G,S,X internal nodes; source-follower COMP; DATA writing with S clamped; 1/2 intentional capacitors on 6 edges; optional drain isolation; 5 stage order"}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("top10", "old_v2_ideal_transfer", "boundary_extension")}, ensure_ascii=False, indent=2))
    print("Top candidate:", top10[0])


if __name__ == "__main__":
    main()
