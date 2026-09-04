#!/usr/bin/env python3
"""Tighter electrostatic pre-screen for an IGZO-DTFT AMOLED pixel.

The V2 grammar is intentionally small. It encodes the two new physical requirements
directly: capacitive DATA compression into VGS and post-write source bootstrapping.
The results are analytical/pre-SPICE and require compact-model verification.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_v2"

PHASES = ("RESET", "COMP", "SOURCE_PREP", "WRITE", "EMIT")
CONTROL_MASKS = {
    "SCAN_C": "11000",
    "SCAN_S": "10110",
    "SCAN_D": "00010",
    "EM": "00001",
}

CAP_ST_FF = (40, 60, 80, 100, 120, 160)
CAP_DATA_FF = (10, 20, 30, 40, 60, 80)
TECHNOLOGIES = ("IGZO", "LTPS")
SWITCH_ROLES = ("GREF", "XREF", "SCLAMP", "DATA", "EM")

# Explicit proxy assumptions. They are ranking aids, not PDK device claims.
TECH = {
    "IGZO": {"ron_ohm": 150_000.0, "goff_s": 2.0e-14},
    "LTPS": {"ron_ohm": 30_000.0, "goff_s": 2.0e-12},
}
CG_PAR_FF = 3.0
CX_PAR_FF = 2.0
CS_LOAD_FF = 20.0
FRAME_HOLD_S = 1.0 / 60.0
TARGET_KAPPA = 1.0 / 3.0
KAPPA_RANGE = (0.20, 0.60)
MAX_VGS_SOURCE_SENSITIVITY = 0.05
MAX_HOLD_DROOP = 0.05
MAX_TOTAL_CAP_FF = 240


@dataclass(frozen=True)
class Timing:
    reset_us: float
    comp_us: float
    source_prep_us: float
    write_us: float
    dead_we_us: float

    @property
    def address_us(self) -> float:
        return (
            self.reset_us
            + self.comp_us
            + self.source_prep_us
            + self.write_us
            + self.dead_we_us
        )


@dataclass(frozen=True)
class Candidate:
    c_st_ff: int
    c_data_ff: int
    gref_tech: str
    xref_tech: str
    sclamp_tech: str
    data_tech: str
    em_tech: str
    timing: Timing

    @property
    def candidate_id(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True).encode()
        return "V2-" + hashlib.sha1(raw).hexdigest()[:10].upper()


def compression_ratio(
    c_st_ff: float, c_data_ff: float, cg_par_ff: float = CG_PAR_FF
) -> float:
    """ΔVGS/ΔVDATA while S is clamped and X is driven."""
    return c_data_ff / (c_st_ff + c_data_ff + cg_par_ff)


def source_tracking_gain(
    c_st_ff: float,
    c_data_ff: float,
    cg_par_ff: float = CG_PAR_FF,
    cx_par_ff: float = CX_PAR_FF,
) -> float:
    """ΔVG/ΔVS after DATA is disconnected and X is floating.

    The two floating-node charge-conservation equations include parasitics from G and
    X to AC ground. Ideal VGS preservation is a gain of one.
    """
    a = c_st_ff + c_data_ff + cg_par_ff
    d = c_data_ff + cx_par_ff
    determinant = a * d - c_data_ff**2
    return c_st_ff * d / determinant


def robustness_envelope(c_st_ff: float, c_data_ff: float) -> dict:
    """Cap mismatch ±10% and node-parasitic ±50% corner envelope."""
    values = []
    for st_scale, data_scale, cg_par, cx_par in itertools.product(
        (0.9, 1.1),
        (0.9, 1.1),
        (0.5 * CG_PAR_FF, 1.5 * CG_PAR_FF),
        (0.5 * CX_PAR_FF, 1.5 * CX_PAR_FF),
    ):
        st = c_st_ff * st_scale
        data = c_data_ff * data_scale
        kappa = compression_ratio(st, data, cg_par)
        sensitivity = abs(1.0 - source_tracking_gain(st, data, cg_par, cx_par))
        values.append((kappa, sensitivity))
    return {
        "corner_count": len(values),
        "compression_ratio_min": min(value[0] for value in values),
        "compression_ratio_max": max(value[0] for value in values),
        "worst_vgs_source_sensitivity_pct": 100.0 * max(value[1] for value in values),
    }


def v1_series_cap_tracking() -> dict:
    """Approximate source tracking of the V1 40 fF--40 fF series-cap winner."""
    c1 = 40.0
    c2 = 40.0
    cgs = 3.0
    cg_par = 2.0
    ca_par = 2.0
    a = c1 + cgs + cg_par
    b = -c1
    d = c1 + c2 + ca_par
    rhs_g = cgs
    rhs_a = c2
    determinant = a * d - b * b
    tracking = (rhs_g * d - b * rhs_a) / determinant
    return {
        "source_tracking_gain": tracking,
        "vgs_source_sensitivity_pct": 100.0 * abs(1.0 - tracking),
        "passes_v2_5pct_gate": abs(1.0 - tracking) <= MAX_VGS_SOURCE_SENSITIVITY,
    }


def effective_data_cap_ff(c_st_ff: float, c_data_ff: float) -> float:
    gate_to_ground = c_st_ff + CG_PAR_FF
    return CX_PAR_FF + c_data_ff * gate_to_ground / (c_data_ff + gate_to_ground)


def effective_source_cap_ff(c_st_ff: float, c_data_ff: float) -> float:
    gate_branch = c_st_ff * (c_data_ff + CG_PAR_FF) / (
        c_st_ff + c_data_ff + CG_PAR_FF
    )
    return CS_LOAD_FF + gate_branch


def settling_fraction(duration_us: float, ron_ohm: float, cap_ff: float) -> float:
    tau_s = ron_ohm * cap_ff * 1e-15
    return 1.0 - math.exp(-(duration_us * 1e-6) / tau_s)


def compensation_settling(c_st_ff: float, comp_us: float) -> float:
    # Calibrated only to the V1 behavioral baseline: 40 fF needs roughly 16 us.
    tau_us = 3.5 * c_st_ff / 40.0
    return 1.0 - math.exp(-comp_us / tau_us)


def hold_droop(candidate: Candidate, kappa: float) -> float:
    # Leakage at X is coupled to VGS approximately by kappa squared.
    g_gate = TECH[candidate.gref_tech]["goff_s"]
    g_x = TECH[candidate.xref_tech]["goff_s"] + TECH[candidate.data_tech]["goff_s"]
    g_equivalent = g_gate + kappa**2 * g_x
    c_hold_f = (candidate.c_st_ff + CG_PAR_FF) * 1e-15
    return 1.0 - math.exp(-FRAME_HOLD_S * g_equivalent / c_hold_f)


def evaluate(candidate: Candidate) -> dict:
    kappa = compression_ratio(candidate.c_st_ff, candidate.c_data_ff)
    tracking = source_tracking_gain(candidate.c_st_ff, candidate.c_data_ff)
    vgs_source_sensitivity = abs(1.0 - tracking)
    droop = hold_droop(candidate, kappa)
    write_settle = settling_fraction(
        candidate.timing.write_us,
        TECH[candidate.data_tech]["ron_ohm"],
        effective_data_cap_ff(candidate.c_st_ff, candidate.c_data_ff),
    )
    source_settle = settling_fraction(
        candidate.timing.source_prep_us,
        TECH[candidate.sclamp_tech]["ron_ohm"],
        effective_source_cap_ff(candidate.c_st_ff, candidate.c_data_ff),
    )
    comp_settle = compensation_settling(candidate.c_st_ff, candidate.timing.comp_us)
    em_drop_mv = 300e-9 * TECH[candidate.em_tech]["ron_ohm"] * 1e3
    total_cap = candidate.c_st_ff + candidate.c_data_ff

    hard_checks = {
        "two_capacitors": True,
        "control_groups_le_5": len(CONTROL_MASKS) <= 5,
        "separate_comp_write": not any(
            mask[1] == "1" and mask[3] == "1" for mask in CONTROL_MASKS.values()
        ),
        "compression_in_range": KAPPA_RANGE[0] <= kappa <= KAPPA_RANGE[1],
        "source_stability": vgs_source_sensitivity <= MAX_VGS_SOURCE_SENSITIVITY,
        "cap_budget": total_cap <= MAX_TOTAL_CAP_FF,
        "comp_settled": comp_settle >= 0.98,
        "source_prep_settled": source_settle >= 0.99,
        "write_settled": write_settle >= 0.99,
        "hold_droop": droop <= MAX_HOLD_DROOP,
        "em_switch_drop": em_drop_mv <= 100.0,
    }
    functional = all(hard_checks.values())

    tracking_score = math.exp(-15.0 * vgs_source_sensitivity)
    compression_score = math.exp(-8.0 * abs(kappa - TARGET_KAPPA))
    hold_score = math.exp(-20.0 * droop)
    speed_score = math.exp(-candidate.timing.address_us / 80.0)
    area_score = math.exp(-total_cap / 400.0)
    em_score = math.exp(-em_drop_mv / 50.0)
    score = 100.0 * (
        0.35 * tracking_score
        + 0.20 * compression_score
        + 0.15 * hold_score
        + 0.15 * speed_score
        + 0.10 * area_score
        + 0.05 * em_score
    )
    if not functional:
        score -= 100.0

    return {
        "functional": functional,
        "score": score,
        "compression_ratio": kappa,
        "source_tracking_gain": tracking,
        "vgs_source_sensitivity_pct": 100.0 * vgs_source_sensitivity,
        "hold_droop_60hz_pct": 100.0 * droop,
        "comp_settling_pct": 100.0 * comp_settle,
        "source_prep_settling_pct": 100.0 * source_settle,
        "write_settling_pct": 100.0 * write_settle,
        "em_drop_at_300na_mv": em_drop_mv,
        "total_cap_ff": total_cap,
        "hard_checks": hard_checks,
    }


def enumerate_candidates() -> list[Candidate]:
    timings = [
        Timing(0.5, comp, prep, write, dead)
        for comp, prep, write, dead in itertools.product(
            (8.0, 16.0, 32.0, 64.0),
            (0.25, 0.5, 1.0),
            (0.25, 0.5, 1.0),
            (0.05, 0.10),
        )
    ]
    candidates = []
    for c_st, c_data in itertools.product(CAP_ST_FF, CAP_DATA_FF):
        for technologies in itertools.product(TECHNOLOGIES, repeat=len(SWITCH_ROLES)):
            for timing in timings:
                candidates.append(Candidate(c_st, c_data, *technologies, timing))
    return candidates


def pareto_ids(rows: list[dict]) -> set[str]:
    fields = (
        "vgs_source_sensitivity_pct",
        "hold_droop_60hz_pct",
        "address_us",
        "total_cap_ff",
    )
    front = set()
    for i, a in enumerate(rows):
        dominated = False
        for j, b in enumerate(rows):
            if i == j:
                continue
            no_worse = all(b[field] <= a[field] for field in fields)
            strictly_better = any(b[field] < a[field] for field in fields)
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            front.add(a["candidate_id"])
    return front


def topology_description(best: dict) -> dict:
    return {
        "transistor_count": 6,
        "capacitor_count": 2,
        "dtft": "IGZO",
        "control_group_count": len(CONTROL_MASKS),
        "phase_order": list(PHASES),
        "control_masks": CONTROL_MASKS,
        "netlist": [
            "M_DRT: VDD -> S; gate=G; technology=IGZO",
            f"C_ST: G -- S ({best['c_st_ff']} fF)",
            f"C_DATA: G -- X ({best['c_data_ff']} fF)",
            f"T_GREF: G -- VREF; control=SCAN_C; technology={best['gref_tech']}",
            f"T_XREF: X -- VREF; control=SCAN_C; technology={best['xref_tech']}",
            f"T_SCLAMP: S -- VINIT; control=SCAN_S; technology={best['sclamp_tech']}",
            f"T_DATA: X -- DATA; control=SCAN_D; technology={best['data_tech']}",
            f"T_EM: S -- OLED_A; control=EM; technology={best['em_tech']}",
            "OLED: OLED_A -> ELVSS",
        ],
    }


def write_report(summary: dict) -> None:
    best = summary["top10"][0]
    stable = summary["stability_first_candidate"]
    topology = summary["recommended_topology"]
    lines = [
        "# V2 紧约束 AMOLED 像素电路初筛",
        "",
        "## 结论",
        "",
        "新约束把最低晶体管数实现收缩为一个 6T2C 核心拓扑：`C_ST` 必须直接跨接 IGZO "
        "DTFT 的 G–S，`C_DATA` 从独立节点 X 耦合到 G。前者负责源极自举，后者负责压缩写入。",
        "",
        f"纯稳定性优先候选：`C_ST={stable['c_st_ff']} fF`、`C_DATA={stable['c_data_ff']} fF`，"
        f"压缩比 `κ={stable['compression_ratio']:.3f}`，源极每变化 1 V 时 VGS 的代理变化为 "
        f"`{stable['vgs_source_sensitivity_pct']:.3f}%`。",
        "",
        f"若压缩目标取 `κ≈1/3`，综合评分候选为 `C_ST={best['c_st_ff']} fF`、"
        f"`C_DATA={best['c_data_ff']} fF`，得到 `κ={best['compression_ratio']:.3f}` 和 "
        f"`{best['vgs_source_sensitivity_pct']:.3f}%` 的 VGS 源极敏感度。",
        "",
        "## 电路连接",
        "",
    ]
    lines.extend(f"- {item}" for item in topology["netlist"])
    lines.extend(
        [
            "",
            "## 五阶段时序",
            "",
            "| 控制组 | RESET | COMP | SOURCE_PREP | WRITE | EMIT |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, mask in CONTROL_MASKS.items():
        lines.append("| " + name + " | " + " | ".join(mask) + " |")
    lines.extend(
        [
            "",
            "`SCAN_C` 同时驱动 GREF/XREF；因此只有 4 组 GOA 控制信号。"
            "`SOURCE_PREP` 先固定 S，再由 `SCAN_D` 写入 DATA，避免把源极切换误当作数据信号。",
            "",
            "最低晶体管数版本中的 `SCAN_S=10110` 是双脉冲波形。若 GOA 要求每组输出只产生一个连续脉冲，"
            "可把 `T_SCLAMP` 拆成 RESET 专用和 SOURCE_PREP+WRITE 专用两只 SWT：电路变为 7T2C，"
            "控制组增至 5 组，仍满足限制；电容网络与压缩/自举方程不变。",
            "",
            "## 关键方程",
            "",
            "写入压缩比：",
            "",
            "```text",
            "κ = ΔVGS/ΔVDATA = C_DATA / (C_ST + C_DATA + C_G,par)",
            "```",
            "",
            "写入后 DATA 断开、X 浮置，源极自举增益：",
            "",
            "```text",
            "βS = ΔVG/ΔVS",
            "VGS 对源极的残余敏感度 = |1 - βS|",
            "```",
            "",
            "## 搜索边界",
            "",
            f"- 原始参数—时序组合：{summary['raw_candidates']:,}",
            f"- 通过全部硬约束：{summary['functional_candidates']:,}",
            f"- 补偿时间≤16 µs 时通过数量：{summary['functional_with_comp_le_16us']:,}",
            f"- 压缩比范围：{KAPPA_RANGE[0]:.2f}–{KAPPA_RANGE[1]:.2f}；排名目标 κ≈1/3",
            f"- 源极稳定性硬门：|ΔVGS/ΔVS|≤{MAX_VGS_SOURCE_SENSITIVITY:.0%}",
            f"- 电容搜索：C_ST={list(CAP_ST_FF)} fF；C_DATA={list(CAP_DATA_FF)} fF；总和≤{MAX_TOTAL_CAP_FF} fF",
            "- STFT 的 IGZO/LTPS 角色分配全部枚举；DTFT 固定 IGZO",
            "",
            "## 对 V1 结果的影响",
            "",
            f"V1 的等值 40 fF 串联双电容拓扑，按同一电荷守恒近似得到 βS="
            f"{summary['v1_comparison']['source_tracking_gain']:.3f}、|ΔVGS/ΔVS|="
            f"{summary['v1_comparison']['vgs_source_sensitivity_pct']:.2f}%。因此它不能通过 V2 的 5% 硬门；"
            "V2 的主存储电容必须从串联中间节点改为直接跨接 G–S。",
            "",
            "## 电容/寄生扰动",
            "",
            f"- 稳定性优先方案：κ={summary['robustness_envelopes']['stability_first']['compression_ratio_min']:.3f}–"
            f"{summary['robustness_envelopes']['stability_first']['compression_ratio_max']:.3f}；最坏 "
            f"|ΔVGS/ΔVS|={summary['robustness_envelopes']['stability_first']['worst_vgs_source_sensitivity_pct']:.2f}%",
            f"- κ≈1/3 方案：κ={summary['robustness_envelopes']['kappa_target']['compression_ratio_min']:.3f}–"
            f"{summary['robustness_envelopes']['kappa_target']['compression_ratio_max']:.3f}；最坏 "
            f"|ΔVGS/ΔVS|={summary['robustness_envelopes']['kappa_target']['worst_vgs_source_sensitivity_pct']:.2f}%",
            "- 扰动网格：C_ST/C_DATA ±10%，G/X 节点寄生 ±50%，共 16 个角点",
            "",
            "## 证据边界",
            "",
            "结果是电荷守恒、RC 建立时间和显式漏电代理构成的 pre-SPICE 筛选。"
            "压缩比和源极自举结论是电容网络结论；补偿时间、60 Hz 保持误差和开关压降仍依赖代理参数。"
            "当前最佳候选的地址代理时间为 65.05 µs，其中补偿占 64 µs；它不是高分辨率面板可直接采用的 timing。"
            "下一轮必须把 DTFT W/L、补偿电流或跨多行补偿加入设计变量。进入版图或论文定量结论前，"
            "还必须接入目标 LTPS/IGZO PDK、OLED 模型与寄生参数。",
            "",
        ]
    )
    (RESULTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    candidates = enumerate_candidates()
    rows = []
    failures: dict[str, int] = {}
    for candidate in candidates:
        metrics = evaluate(candidate)
        for name, passed in metrics.pop("hard_checks").items():
            if not passed:
                failures[name] = failures.get(name, 0) + 1
        row = {
            "candidate_id": candidate.candidate_id,
            "c_st_ff": candidate.c_st_ff,
            "c_data_ff": candidate.c_data_ff,
            "gref_tech": candidate.gref_tech,
            "xref_tech": candidate.xref_tech,
            "sclamp_tech": candidate.sclamp_tech,
            "data_tech": candidate.data_tech,
            "em_tech": candidate.em_tech,
            "address_us": candidate.timing.address_us,
            **asdict(candidate.timing),
            **metrics,
        }
        rows.append(row)

    functional = [row for row in rows if row["functional"]]
    front = pareto_ids(functional)
    for row in rows:
        row["pareto"] = row["candidate_id"] in front
    ranked = sorted(
        functional,
        key=lambda row: (
            -row["score"],
            row["vgs_source_sensitivity_pct"],
            row["address_us"],
        ),
    )
    top10 = ranked[:10]
    if not top10:
        raise RuntimeError("No V2 candidate passed the hard constraints")

    fields = list(rows[0])
    with (RESULTS / "all_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS / "top10.json").write_text(
        json.dumps(top10, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    stability_first = min(
        functional,
        key=lambda row: (
            row["vgs_source_sensitivity_pct"],
            row["total_cap_ff"],
            row["hold_droop_60hz_pct"],
            row["em_drop_at_300na_mv"],
            row["address_us"],
        ),
    )
    summary = {
        "model_class": "electrostatic_rc_pre_spice_v2",
        "raw_candidates": len(rows),
        "functional_candidates": len(functional),
        "functional_with_comp_le_16us": sum(
            row["comp_us"] <= 16.0 for row in functional
        ),
        "pareto_candidates": len(front),
        "failure_counts_nonexclusive": failures,
        "assumptions": {
            "compression_range": list(KAPPA_RANGE),
            "compression_ranking_target": TARGET_KAPPA,
            "max_vgs_source_sensitivity": MAX_VGS_SOURCE_SENSITIVITY,
            "max_total_cap_ff": MAX_TOTAL_CAP_FF,
            "max_hold_droop_60hz": MAX_HOLD_DROOP,
            "cg_par_ff": CG_PAR_FF,
            "cx_par_ff": CX_PAR_FF,
            "technology_proxy": TECH,
        },
        "recommended_topology": topology_description(top10[0]),
        "v1_comparison": v1_series_cap_tracking(),
        "stability_first_candidate": stability_first,
        "robustness_envelopes": {
            "stability_first": robustness_envelope(
                stability_first["c_st_ff"], stability_first["c_data_ff"]
            ),
            "kappa_target": robustness_envelope(top10[0]["c_st_ff"], top10[0]["c_data_ff"]),
        },
        "top10": top10,
    }
    (RESULTS / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "top10"}, ensure_ascii=False, indent=2))
    print("\nTOP 10")
    for index, row in enumerate(top10, 1):
        print(
            index,
            row["candidate_id"],
            f"score={row['score']:.3f}",
            f"kappa={row['compression_ratio']:.3f}",
            f"VGS/VS={row['vgs_source_sensitivity_pct']:.2f}%",
            f"addr={row['address_us']:.2f}us",
        )


if __name__ == "__main__":
    main()
