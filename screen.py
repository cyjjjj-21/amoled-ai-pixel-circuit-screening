#!/usr/bin/env python3
"""Constraint-first initial screen for a-IGZO AMOLED pixel circuits.

The topology grammar is deliberately role based, not an unrestricted transistor graph:
one DRT, two storage capacitors, one REF switch, one compensation switch, one DATA
switch, one OLED isolation switch, one initialization switch and an optional emission
coupling switch.  That bounded grammar is the core conclusion of the literature review.

The transient engine is a behavioral modified-nodal model.  It is suitable for
functional/timing triage only; it is not a replacement for an RPI-62 or Verilog-A model.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

NODES = ("G", "A", "S", "B", "O")
NI = {name: i for i, name in enumerate(NODES)}
PHASE_BIT = {"R": 0, "C": 1, "W": 2, "E": 3}
ALLOWED_MASKS = {"1000", "1100", "0100", "0110", "0010", "0001", "1001", "1110"}


@dataclass(frozen=True)
class Switch:
    name: str
    left: str
    right: str
    mask: str


@dataclass(frozen=True)
class Topology:
    c1_other: str
    comp_node: str
    data_node: str
    anchor_node: str
    bridge_node: str | None
    anchor_mask: str
    em_mask: str

    def switches(self) -> tuple[Switch, ...]:
        sw = [
            Switch("T1_REF", "REF", "G", "1100"),
            Switch("T2_COMP", self.comp_node, "S", "1100"),
            Switch("T3_DATA", "DATA", self.data_node, "0010"),
            Switch("T4_EM", "S", "O", self.em_mask),
            Switch("T5_INIT", self.anchor_node, "GND", self.anchor_mask),
        ]
        if self.bridge_node is not None:
            sw.append(Switch("T6_EM_COUPLE", self.bridge_node, "O", self.em_mask))
        return tuple(sw)

    @property
    def transistor_count(self) -> int:
        return 1 + len(self.switches())

    @property
    def topology_id(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True).encode()
        return "PX-" + hashlib.sha1(raw).hexdigest()[:8].upper()

    def netlist(self) -> list[str]:
        lines = [
            "DRT: VDD -> S; gate=G",
            f"C1_TH: G -- {self.c1_other} (40 fF)",
            "C2_DATA: A -- B (40 fF)",
        ]
        lines.extend(f"{s.name}: {s.left} -- {s.right}; ON={s.mask}" for s in self.switches())
        lines.append("OLED: O -> GND")
        return lines


@dataclass(frozen=True)
class Timing:
    t_reset_us: float
    t_comp_us: float
    t_write_us: float
    t_dead_cw_us: float
    t_dead_we_us: float
    # Emission sampling window. It is excluded from address time.
    t_emit_us: float = 6.0

    @property
    def address_us(self) -> float:
        return self.t_reset_us + self.t_comp_us + self.t_write_us + self.t_dead_cw_us + self.t_dead_we_us

    @property
    def timing_id(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True).encode()
        return "TM-" + hashlib.sha1(raw).hexdigest()[:8].upper()


def mask_on(mask: str, segment: str) -> bool:
    if segment in PHASE_BIT:
        return mask[PHASE_BIT[segment]] == "1"
    if segment == "CW":
        return mask[1] == "1" and mask[2] == "1"
    if segment == "WE":
        return mask[2] == "1" and mask[3] == "1"
    raise ValueError(segment)


def canonical_key(t: Topology) -> str:
    """Canonicalize the interchangeable internal labels A and B."""

    def encoded(x: Topology) -> str:
        return json.dumps(asdict(x), sort_keys=True, separators=(",", ":"))

    swap = {"A": "B", "B": "A", "G": "G", "S": "S", "O": "O", None: None}
    t2 = Topology(
        c1_other=swap[t.c1_other],
        comp_node=swap[t.comp_node],
        data_node=swap[t.data_node],
        anchor_node=swap[t.anchor_node],
        bridge_node=swap[t.bridge_node],
        anchor_mask=t.anchor_mask,
        em_mask=t.em_mask,
    )
    return min(encoded(t), encoded(t2))


def hard_filter(t: Topology) -> tuple[bool, str]:
    switches = t.switches()
    if t.transistor_count not in (6, 7):
        return False, "outside_5T2C_to_7T2C"
    if any(s.mask not in ALLOWED_MASKS for s in switches):
        return False, "mask_not_allowed"
    if len({s.mask for s in switches}) > 4:
        return False, "more_than_four_controls"
    if t.comp_node != t.c1_other:
        return False, "threshold_cap_not_on_comp_path"
    if t.data_node != t.c1_other:
        return False, "data_not_on_programming_plate"
    far_plate = "B" if t.c1_other == "A" else "A"
    if t.anchor_node != far_plate:
        return False, "data_cap_far_plate_not_initialized"
    if t.bridge_node is not None and t.bridge_node != far_plate:
        return False, "post_comp_switch_touches_threshold_storage"
    if t.anchor_mask not in ("1110", "1100"):
        return False, "far_plate_not_held_through_comp"
    if any(mask_on(s.mask, p) for s in switches if s.name.startswith("T4") or s.name.startswith("T6") for p in ("C", "W")):
        return False, "oled_path_on_during_address"
    if mask_on("0010", "C"):
        return False, "data_on_during_comp"
    return True, "pass"


def enumerate_topologies() -> tuple[list[Topology], Counter]:
    raw = []
    reasons: Counter = Counter()
    for vals in itertools.product(
        ("A", "B"),  # C1 other terminal
        ("A", "B"),  # compensation node
        ("A", "B"),  # data node
        ("A", "B"),  # C2 far-plate initialization node
        (None, "A", "B"),  # optional emission coupling
        ("1110", "1100", "1000"),
        ("1001", "0001"),
    ):
        raw.append(Topology(*vals))

    dedup: dict[str, Topology] = {}
    for t in raw:
        ok, reason = hard_filter(t)
        if not ok:
            reasons[reason] += 1
            continue
        key = canonical_key(t)
        if key in dedup:
            reasons["graph_isomorphic_duplicate"] += 1
            continue
        dedup[key] = t
    reasons["raw_generated"] = len(raw)
    reasons["hard_pass_nonisomorphic"] = len(dedup)
    return list(dedup.values()), reasons


def enumerate_timings() -> list[Timing]:
    return [
        Timing(r, c, w, dcw, dwe)
        for r, c, w, dcw, dwe in itertools.product(
            (0.5, 1.0),
            (1.0, 2.0, 4.0, 8.0, 16.0),
            (0.5, 1.0, 2.0),
            (0.05, 0.10),
            (0.05, 0.10),
        )
    ]


class BehavioralSimulator:
    """Small modified-nodal transient proxy with idealized oxide TFT behavior."""

    VDD = 8.5
    VREF = 2.0
    VTH0 = -0.67
    BETA = 22.56e-9  # A/V^2; makes the ideal 5 V point roughly 282 nA
    OLED_K = 220e-9  # A/V^2
    OLED_VON = 1.8
    OLED_I0 = 50e-12
    OLED_N = 0.25
    SUBTHRESHOLD_SWING = 0.338  # V/dec, measured value reported by Park et al.
    DRT_I_AT_THRESHOLD = 66.7e-12
    G_ON = 1.0 / 50_000.0
    G_OFF = 1e-12
    C1 = 40e-15
    C2 = 40e-15
    C_PAR = 2e-15
    C_GS = 3e-15
    C_OLED = 20e-15

    def __init__(self, topology: Topology):
        self.t = topology
        self.C = np.eye(len(NODES)) * self.C_PAR
        self._add_cap("G", topology.c1_other, self.C1)
        self._add_cap("A", "B", self.C2)
        self._add_cap("G", "S", self.C_GS)
        self.C[NI["O"], NI["O"]] += self.C_OLED

    def _add_cap(self, a: str, b: str, value: float) -> None:
        ia, ib = NI[a], NI[b]
        self.C[ia, ia] += value
        self.C[ib, ib] += value
        self.C[ia, ib] -= value
        self.C[ib, ia] -= value

    @staticmethod
    def _fixed(name: str, data: np.ndarray) -> np.ndarray:
        if name == "VDD":
            return np.full_like(data, BehavioralSimulator.VDD)
        if name == "REF":
            return np.full_like(data, BehavioralSimulator.VREF)
        if name == "GND":
            return np.zeros_like(data)
        if name == "DATA":
            return data
        raise ValueError(name)

    def _linear_system(self, segment: str, dt: float, data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        ncorner = len(data)
        L = np.zeros((len(NODES), len(NODES)))
        fixed = np.zeros((ncorner, len(NODES)))
        for sw in self.t.switches():
            g = self.G_ON if mask_on(sw.mask, segment) else self.G_OFF
            l_internal = sw.left in NI
            r_internal = sw.right in NI
            if l_internal and r_internal:
                i, j = NI[sw.left], NI[sw.right]
                L[i, i] += g
                L[j, j] += g
                L[i, j] -= g
                L[j, i] -= g
            elif l_internal:
                i = NI[sw.left]
                L[i, i] += g
                fixed[:, i] += g * self._fixed(sw.right, data)
            elif r_internal:
                i = NI[sw.right]
                L[i, i] += g
                fixed[:, i] += g * self._fixed(sw.left, data)
            else:
                raise ValueError(f"switch without internal node: {sw}")
        mat = self.C / dt + L
        return np.linalg.inv(mat), fixed

    def run(self, timing: Timing) -> dict:
        vth_shift = np.repeat(np.array([-0.5, 0.0, 0.5]), 6)
        data = np.tile(np.repeat(np.array([-0.2, 2.4, 5.0]), 2), 3)
        prior = np.tile(np.array([0.6, 4.8]), 9)
        ncorner = len(data)
        v = np.column_stack([prior, prior, np.full(ncorner, 2.0), prior * 0.3, np.zeros(ncorner)])
        vth = self.VTH0 + vth_shift

        segments = [
            ("R", timing.t_reset_us),
            ("C", timing.t_comp_us),
            ("CW", timing.t_dead_cw_us),
            ("W", timing.t_write_us),
            ("WE", timing.t_dead_we_us),
            ("E", timing.t_emit_us),
        ]
        emit_samples: list[np.ndarray] = []
        off_samples: list[np.ndarray] = []
        vgs_samples: list[np.ndarray] = []
        c1_end_comp = None
        stage_end = {}

        for segment, duration_us in segments:
            steps = 48 if segment in ("R", "C", "W", "E") else 12
            dt = duration_us * 1e-6 / steps
            inv, fixed = self._linear_system(segment, dt, data)
            for step in range(steps):
                vg, vs, vo = v[:, NI["G"]], v[:, NI["S"]], v[:, NI["O"]]
                over = np.maximum(vg - vs - vth, 0.0)
                headroom = np.clip((self.VDD - vs) / 0.4, 0.0, 1.0)
                sub = self.DRT_I_AT_THRESHOLD * 10.0 ** (
                    np.clip(vg - vs - vth, -4.0, 0.0) / self.SUBTHRESHOLD_SWING
                )
                idrt = (sub + 0.5 * self.BETA * over**2) * headroom
                oled_sub = self.OLED_I0 * np.exp(np.clip((vo - self.OLED_VON) / self.OLED_N, -40.0, 8.0))
                ioled = oled_sub + self.OLED_K * np.maximum(vo - self.OLED_VON, 0.0) ** 2
                nonlin = np.zeros_like(v)
                nonlin[:, NI["S"]] += idrt
                nonlin[:, NI["O"]] -= ioled
                rhs = v @ (self.C / dt).T + fixed + nonlin
                v = rhs @ inv.T
                v = np.clip(v, -12.0, 13.0)
                if step >= steps // 2:
                    if segment == "E":
                        # At low gray, explicitly charging the OLED capacitance to its
                        # millisecond-scale steady state would dominate runtime.  The
                        # series-path current is therefore represented by DRT current;
                        # this is the same steady current that must flow through OLED.
                        emit_samples.append(idrt.copy())
                        vgs_samples.append((vg - vs).copy())
                    elif segment in ("R", "C", "W"):
                        off_samples.append(ioled.copy())
            stage_end[segment] = v.copy()
            if segment == "C":
                c1_end_comp = v[:, NI["G"]] - v[:, NI[self.t.c1_other]]

        emit = np.mean(np.stack(emit_samples), axis=0)
        vgs_emit = np.mean(np.stack(vgs_samples), axis=0)
        off_max = float(np.max(np.stack(off_samples))) if off_samples else 0.0
        assert c1_end_comp is not None

        # Reshape as [vth, data, prior].
        I = emit.reshape(3, 3, 2)
        VGS = vgs_emit.reshape(3, 3, 2)
        C1V = c1_end_comp.reshape(3, 3, 2)
        nominal = I[1]
        denom = np.maximum(nominal, 50e-12)
        rcer = np.abs((I[[0, 2]] - nominal[None, :, :]) / denom[None, :, :])
        prior_err = np.abs(nominal[:, 1] - nominal[:, 0]) / np.maximum(np.mean(nominal, axis=1), 50e-12)
        data_curve = np.mean(nominal, axis=1)
        monotonic_margin = float(np.min(np.diff(data_curve)))
        s_th = float(np.mean((C1V[2] - C1V[0]) / 1.0))
        g_data = float(np.mean((VGS[1, 2] - VGS[1, 0]) / 5.2))
        low_current = float(np.mean(nominal[0]))
        high_current = float(np.mean(nominal[2]))

        max_rcer = float(np.max(rcer))
        max_prior = float(np.max(prior_err))
        functional = (
            monotonic_margin > 0
            and high_current > 5e-9
            and off_max < 5e-9
            and max_rcer < 1.0
            and max_prior < 0.5
            and 0.25 < abs(s_th) < 1.75
            and 0.15 < abs(g_data) < 1.75
        )

        # Score is intentionally explicit and bounded. Lower error and shorter address
        # time dominate; 6T gets a small area credit, never enough to offset bad function.
        err_score = math.exp(-4.0 * max_rcer)
        prior_score = math.exp(-4.0 * max_prior)
        off_score = math.exp(-off_max / 1e-9)
        sth_score = math.exp(-1.5 * abs(abs(s_th) - 1.0))
        data_score = math.exp(-1.2 * abs(abs(g_data) - 1.0))
        speed_score = math.exp(-timing.address_us / 40.0)
        area_score = 1.0 if self.t.transistor_count == 6 else 0.88
        score = 100.0 * (
            0.30 * err_score
            + 0.14 * prior_score
            + 0.10 * off_score
            + 0.16 * sth_score
            + 0.14 * data_score
            + 0.10 * speed_score
            + 0.06 * area_score
        )
        if not functional:
            score -= 100.0

        return {
            "functional": functional,
            "score": score,
            "max_rcer_pct": 100 * max_rcer,
            "max_prior_error_pct": 100 * max_prior,
            "off_current_nA": off_max * 1e9,
            "low_current_nA": low_current * 1e9,
            "mid_current_nA": float(np.mean(nominal[1])) * 1e9,
            "high_current_nA": high_current * 1e9,
            "s_th": s_th,
            "g_data": g_data,
            "monotonic_margin_nA": monotonic_margin * 1e9,
        }


def pareto_front(rows: list[dict]) -> set[str]:
    """Pareto set over error, address time and transistor count."""
    front: set[str] = set()
    for i, a in enumerate(rows):
        dominated = False
        for j, b in enumerate(rows):
            if i == j:
                continue
            no_worse = (
                b["max_rcer_pct"] <= a["max_rcer_pct"]
                and b["address_us"] <= a["address_us"]
                and b["transistor_count"] <= a["transistor_count"]
            )
            strictly = (
                b["max_rcer_pct"] < a["max_rcer_pct"]
                or b["address_us"] < a["address_us"]
                or b["transistor_count"] < a["transistor_count"]
            )
            if no_worse and strictly:
                dominated = True
                break
        if not dominated:
            front.add(a["candidate_id"])
    return front


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    topologies, reasons = enumerate_topologies()
    timings = enumerate_timings()
    rows: list[dict] = []
    for topology in topologies:
        sim = BehavioralSimulator(topology)
        for timing in timings:
            metrics = sim.run(timing)
            row = {
                "candidate_id": f"{topology.topology_id}+{timing.timing_id}",
                "topology_id": topology.topology_id,
                "timing_id": timing.timing_id,
                "transistor_count": topology.transistor_count,
                "c1_other": topology.c1_other,
                "comp_node": topology.comp_node,
                "data_node": topology.data_node,
                "anchor_node": topology.anchor_node,
                "bridge_node": topology.bridge_node or "NONE",
                "anchor_mask": topology.anchor_mask,
                "em_mask": topology.em_mask,
                "address_us": timing.address_us,
                **asdict(timing),
                **metrics,
            }
            rows.append(row)

    functional = [r for r in rows if r["functional"]]
    front = pareto_front(functional)
    for r in rows:
        r["pareto"] = r["candidate_id"] in front
    ranked = sorted(functional, key=lambda r: (-r["score"], r["address_us"], r["max_rcer_pct"]))
    top10 = ranked[:10]

    fieldnames = list(rows[0].keys()) if rows else []
    with (RESULTS / "all_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with (RESULTS / "top10.json").open("w", encoding="utf-8") as f:
        json.dump(top10, f, ensure_ascii=False, indent=2)

    topology_catalog = {
        t.topology_id: {
            **asdict(t),
            "transistor_count": t.transistor_count,
            "netlist": t.netlist(),
        }
        for t in topologies
    }
    summary = {
        "model_class": "behavioral_pre_spice",
        "raw_topologies": reasons["raw_generated"],
        "hard_pass_nonisomorphic_topologies": len(topologies),
        "timings_per_topology": len(timings),
        "simulated_combinations": len(rows),
        "corners_per_combination": 18,
        "total_transient_runs": len(rows) * 18,
        "functional_combinations": len(functional),
        "pareto_combinations": len(front),
        "elimination_reasons": dict(reasons),
        "topologies": topology_catalog,
        "top10": top10,
        "score_weights": {
            "max_rcer": 0.30,
            "prior_frame_independence": 0.14,
            "non_emission_leakage": 0.10,
            "threshold_storage_sensitivity": 0.16,
            "data_gain": 0.14,
            "address_speed": 0.10,
            "transistor_count": 0.06,
        },
        "corner_grid": {
            "delta_vth_V": [-0.5, 0.0, 0.5],
            "vdata_V": [-0.2, 2.4, 5.0],
            "previous_frame_state_V": [0.6, 4.8],
        },
    }
    with (RESULTS / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps({k: v for k, v in summary.items() if k not in ("topologies", "top10")}, indent=2))
    print("\nTOP 10")
    for i, row in enumerate(top10, 1):
        print(i, row["candidate_id"], f"score={row['score']:.3f}", f"RCER={row['max_rcer_pct']:.2f}%", f"addr={row['address_us']:.2f}us")


if __name__ == "__main__":
    main()
