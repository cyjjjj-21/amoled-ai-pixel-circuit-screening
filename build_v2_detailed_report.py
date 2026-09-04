#!/usr/bin/env python3
"""Build the complete V2 technical-report artifact from reviewed screening results."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_v2"


def number(row: dict, key: str) -> float:
    return float(row[key])


def integerish(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value


def read_rows() -> list[dict]:
    with (RESULTS / "all_candidates.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sequential_funnel(rows: list[dict]) -> list[dict]:
    rules = [
        ("01 生成全部参数—时序组合", lambda row: True),
        ("02 压缩比 0.20–0.60", lambda row: 0.20 <= number(row, "compression_ratio") <= 0.60),
        ("03 |ΔVGS/ΔVS| ≤ 5%", lambda row: number(row, "vgs_source_sensitivity_pct") <= 5.0),
        ("04 总电容 ≤ 240 fF", lambda row: number(row, "total_cap_ff") <= 240.0),
        ("05 补偿建立率 ≥ 98%", lambda row: number(row, "comp_settling_pct") >= 98.0),
        (
            "06 Source/Data 建立率 ≥ 99%",
            lambda row: number(row, "source_prep_settling_pct") >= 99.0
            and number(row, "write_settling_pct") >= 99.0,
        ),
        ("07 60 Hz 保持跌落 ≤ 5%", lambda row: number(row, "hold_droop_60hz_pct") <= 5.0),
        ("08 EM 压降 ≤ 100 mV", lambda row: number(row, "em_drop_at_300na_mv") <= 100.0),
    ]
    surviving = rows
    output = []
    previous = len(rows)
    for stage, predicate in rules:
        surviving = [row for row in surviving if predicate(row)]
        count = len(surviving)
        output.append(
            {
                "stage": stage,
                "remaining": count,
                "removed_at_stage": previous - count,
                "retention_pct": 100.0 * count / len(rows),
            }
        )
        previous = count
    return output


def cap_pair_candidates(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in rows:
        if row["functional"] == "True":
            grouped[(int(row["c_st_ff"]), int(row["c_data_ff"]))].append(row)

    output = []
    for (c_st, c_data), group in grouped.items():
        best = max(group, key=lambda row: number(row, "score"))
        output.append(
            {
                "cap_pair": f"{c_st}/{c_data}",
                "c_st_ff": c_st,
                "c_data_ff": c_data,
                "c_st_group": f"CST {c_st} fF",
                "compression_ratio": number(best, "compression_ratio"),
                "vgs_source_sensitivity_pct": number(best, "vgs_source_sensitivity_pct"),
                "hold_droop_pct": number(best, "hold_droop_60hz_pct"),
                "best_address_us": min(number(row, "address_us") for row in group),
                "best_score": number(best, "score"),
                "passing_combinations": len(group),
                "pareto_cap_pair": any(row["pareto"] == "True" for row in group),
                "best_switch_mix": "/".join(
                    best[key] for key in ("gref_tech", "xref_tech", "sclamp_tech", "data_tech", "em_tech")
                ),
            }
        )
    return sorted(output, key=lambda row: (row["c_st_ff"], row["c_data_ff"]))


def timing_candidates(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[float, ...], list[dict]] = defaultdict(list)
    for row in rows:
        if row["functional"] != "True":
            continue
        key = tuple(number(row, field) for field in ("reset_us", "comp_us", "source_prep_us", "write_us", "dead_we_us"))
        grouped[key].append(row)
    output = []
    for key, group in grouped.items():
        best = max(group, key=lambda row: number(row, "score"))
        output.append(
            {
                "timing": "/".join(f"{value:g}" for value in key),
                "reset_us": key[0],
                "comp_us": key[1],
                "source_prep_us": key[2],
                "write_us": key[3],
                "dead_we_us": key[4],
                "address_us": number(best, "address_us"),
                "passing_combinations": len(group),
                "best_score": number(best, "score"),
                "best_cap_pair": f"{best['c_st_ff']}/{best['c_data_ff']}",
                "best_candidate": best["candidate_id"],
            }
        )
    return sorted(output, key=lambda row: (-row["best_score"], row["address_us"]))[:12]


def near_miss_timings(rows: list[dict]) -> list[dict]:
    output = []
    for comp_us in (8.0, 16.0, 32.0, 64.0):
        selected = next(
            row
            for row in rows
            if int(row["c_st_ff"]) == 160
            and int(row["c_data_ff"]) == 80
            and row["gref_tech"] == "IGZO"
            and row["xref_tech"] == "IGZO"
            and row["sclamp_tech"] == "IGZO"
            and row["data_tech"] == "IGZO"
            and row["em_tech"] == "LTPS"
            and number(row, "comp_us") == comp_us
            and number(row, "source_prep_us") == 0.25
            and number(row, "write_us") == 0.25
            and number(row, "dead_we_us") == 0.05
        )
        comp_settling = number(selected, "comp_settling_pct")
        output.append(
            {
                "candidate": selected["candidate_id"],
                "comp_us": comp_us,
                "address_us": number(selected, "address_us"),
                "comp_settling_pct": comp_settling,
                "functional": selected["functional"] == "True",
                "decision": "通过" if selected["functional"] == "True" else "淘汰：补偿建立不足",
                "gap_to_98pp": comp_settling - 98.0,
            }
        )
    return output


def technology_strategies(rows: list[dict]) -> list[dict]:
    strategies = [
        ("全 IGZO SWT", lambda row: all(row[key] == "IGZO" for key in ("gref_tech", "xref_tech", "sclamp_tech", "data_tech", "em_tech"))),
        ("仅 EM 用 LTPS", lambda row: all(row[key] == "IGZO" for key in ("gref_tech", "xref_tech", "sclamp_tech", "data_tech")) and row["em_tech"] == "LTPS"),
        ("DATA 用 LTPS", lambda row: row["data_tech"] == "LTPS" and row["gref_tech"] == "IGZO"),
        ("XREF 用 LTPS", lambda row: row["xref_tech"] == "LTPS" and row["gref_tech"] == "IGZO"),
        ("GREF 用 LTPS", lambda row: row["gref_tech"] == "LTPS"),
    ]
    output = []
    for label, predicate in strategies:
        population = [row for row in rows if predicate(row)]
        passing = [row for row in population if row["functional"] == "True"]
        best = max(passing, key=lambda row: number(row, "score")) if passing else None
        output.append(
            {
                "strategy": label,
                "evaluated": len(population),
                "passing": len(passing),
                "pass_rate_pct": 100.0 * len(passing) / len(population) if population else 0.0,
                "best_score": number(best, "score") if best else None,
                "best_hold_droop_pct": number(best, "hold_droop_60hz_pct") if best else None,
                "best_em_drop_mv": number(best, "em_drop_at_300na_mv") if best else None,
                "interpretation": (
                    "最高分角色分配；低漏电存储开关 + 低压降 EM"
                    if label == "仅 EM 用 LTPS"
                    else "G 节点漏电越过 5% 保持门" if label == "GREF 用 LTPS" else "存在可行点，需 PDK 决定速度/漏电权衡"
                ),
            }
        )
    return output


def top10_rows(summary: dict) -> list[dict]:
    output = []
    for rank, row in enumerate(summary["top10"], 1):
        output.append(
            {
                "rank": rank,
                "candidate": row["candidate_id"],
                "caps_ff": f"{row['c_st_ff']}/{row['c_data_ff']}",
                "switch_mix": "/".join(
                    row[key] for key in ("gref_tech", "xref_tech", "sclamp_tech", "data_tech", "em_tech")
                ),
                "timing_us": "/".join(
                    f"{row[key]:g}" for key in ("reset_us", "comp_us", "source_prep_us", "write_us", "dead_we_us")
                ),
                "address_us": row["address_us"],
                "compression_ratio": row["compression_ratio"],
                "vgs_source_sensitivity_pct": row["vgs_source_sensitivity_pct"],
                "hold_droop_pct": row["hold_droop_60hz_pct"],
                "score": row["score"],
                "pareto": row["pareto"],
            }
        )
    return output


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> list[str]:
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        values = []
        for field, _ in columns:
            value = row.get(field, "")
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> None:
    rows = read_rows()
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    funnel = sequential_funnel(rows)
    cap_pairs = cap_pair_candidates(rows)
    timings = timing_candidates(rows)
    near_miss = near_miss_timings(rows)
    technologies = technology_strategies(rows)
    ranked = top10_rows(summary)

    circuit_families = [
        {"family": "F1 6T2C-GS-Shared", "T/C": "6T2C", "controls": 4, "storage": "CST: G–S", "data_path": "CDATA: G–X", "status": "通过", "reason": "最少晶体管；SCAN_S 为 10110 双脉冲"},
        {"family": "F2 7T2C-GS-Split", "T/C": "7T2C", "controls": 5, "storage": "CST: G–S", "data_path": "CDATA: G–X", "status": "条件通过", "reason": "拆分 RESET/HOLD 开关；电气核心与 F1 等价"},
        {"family": "F3 7T2C-Series-V1", "T/C": "7T2C", "controls": 4, "storage": "G–A–B–S 串联", "data_path": "DATA→A", "status": "淘汰", "reason": "|ΔVGS/ΔVS|=11.67%，超过 5%"},
        {"family": "F4 6T2C-Source-Inject", "T/C": "6T2C", "controls": 4, "storage": "CST: G–S", "data_path": "CDATA: S–X", "status": "淘汰", "reason": "WRITE 时 S 被钳位，数据增益趋近 0"},
        {"family": "F5 5T2C-Merged-Hold/EM", "T/C": "5T2C", "controls": 3, "storage": "CST: G–S", "data_path": "CDATA: G–X", "status": "淘汰", "reason": "无法独立完成 S 钳位、OLED 隔离和发光连接"},
    ]
    netlist = [
        {"family": "F1/F2", "device": "M_DRT", "connection": "VDD → S; gate=G", "control": "—", "recommended_tech": "IGZO"},
        {"family": "F1/F2", "device": "C_ST", "connection": "G ↔ S", "control": "—", "recommended_tech": "160 fF"},
        {"family": "F1/F2", "device": "C_DATA", "connection": "G ↔ X", "control": "—", "recommended_tech": "60 fF 稳定优先 / 80 fF κ≈1/3"},
        {"family": "F1/F2", "device": "T_GREF", "connection": "G ↔ VREF", "control": "SCAN_C", "recommended_tech": "IGZO"},
        {"family": "F1/F2", "device": "T_XREF", "connection": "X ↔ VREF", "control": "SCAN_C", "recommended_tech": "IGZO"},
        {"family": "F1", "device": "T_SCLAMP", "connection": "S ↔ VINIT", "control": "SCAN_S=10110", "recommended_tech": "IGZO/LTPS 均可"},
        {"family": "F2", "device": "T_SRESET", "connection": "S ↔ VINIT", "control": "RESET_S=10000", "recommended_tech": "IGZO/LTPS 均可"},
        {"family": "F2", "device": "T_SHOLD", "connection": "S ↔ VINIT", "control": "HOLD_S=00110", "recommended_tech": "IGZO/LTPS 均可"},
        {"family": "F1/F2", "device": "T_DATA", "connection": "X ↔ DATA", "control": "SCAN_D", "recommended_tech": "IGZO 优先"},
        {"family": "F1/F2", "device": "T_EM", "connection": "S ↔ OLED_A", "control": "EM", "recommended_tech": "LTPS 优先"},
        {"family": "F1/F2", "device": "OLED", "connection": "OLED_A → ELVSS", "control": "—", "recommended_tech": "OLED 模型待接入"},
    ]
    control_timing = [
        {"signal": "SCAN_C", "reset": 1, "comp": 1, "source_prep": 0, "write": 0, "emit": 0, "devices": "T_GREF, T_XREF"},
        {"signal": "SCAN_S (F1)", "reset": 1, "comp": 0, "source_prep": 1, "write": 1, "emit": 0, "devices": "T_SCLAMP"},
        {"signal": "RESET_S (F2)", "reset": 1, "comp": 0, "source_prep": 0, "write": 0, "emit": 0, "devices": "T_SRESET"},
        {"signal": "HOLD_S (F2)", "reset": 0, "comp": 0, "source_prep": 1, "write": 1, "emit": 0, "devices": "T_SHOLD"},
        {"signal": "SCAN_D", "reset": 0, "comp": 0, "source_prep": 0, "write": 1, "emit": 0, "devices": "T_DATA"},
        {"signal": "EM", "reset": 0, "comp": 0, "source_prep": 0, "write": 0, "emit": 1, "devices": "T_EM"},
    ]
    robustness = [
        {"candidate": "稳定优先 160/60 fF", "nominal_kappa": 0.2690583, "nominal_sensitivity_pct": 2.99237, "corner_kappa": "0.230–0.312", "worst_sensitivity_pct": 4.86859, "corner_definition": "CST/CDATA ±10%; CG/CX parasitic ±50%"},
        {"candidate": "κ≈1/3 160/80 fF", "nominal_kappa": 0.3292181, "nominal_sensitivity_pct": 3.00163, "corner_kappa": "0.285–0.377", "worst_sensitivity_pct": 4.88841, "corner_definition": "CST/CDATA ±10%; CG/CX parasitic ±50%"},
    ]
    hard_filters = [
        {"category": "Topology", "criterion": "C_ST 直接跨接 G–S；C_DATA 连接 G–X；写后 X 浮置", "threshold": "必须满足", "purpose": "把 VTH 保存、数据压缩和源极自举分工"},
        {"category": "Control", "criterion": "Comp 与 Write 无共同导通控制；GOA 组数", "threshold": "≤5", "purpose": "保证补偿与写入物理分离"},
        {"category": "Compression", "criterion": "κ=ΔVGS/ΔVDATA", "threshold": "0.20–0.60", "purpose": "要求显式、可调且小于 1 的写入增益"},
        {"category": "Source stability", "criterion": "|1−ΔVG/ΔVS|", "threshold": "≤5%", "purpose": "写入后源极变化不显著改变 VGS"},
        {"category": "Cap area", "criterion": "C_ST+C_DATA", "threshold": "≤240 fF", "purpose": "阻止靠无限增大 C_ST 获得无界稳定性"},
        {"category": "Timing", "criterion": "补偿 / Source Prep / Write 建立率", "threshold": "≥98% / 99% / 99%", "purpose": "排除尚未建立的快速时序"},
        {"category": "Retention", "criterion": "60 Hz 一帧的 VGS 保持跌落代理", "threshold": "≤5%", "purpose": "排除存储节点 LTPS 漏电过大的组合"},
        {"category": "Emission", "criterion": "300 nA 时 EM 开关压降代理", "threshold": "≤100 mV", "purpose": "控制发光路径损耗"},
    ]

    report_summary = [{
        "structural_families": len(circuit_families),
        "raw_candidates": len(rows),
        "functional_candidates": sum(row["functional"] == "True" for row in rows),
        "pass_rate": sum(row["functional"] == "True" for row in rows) / len(rows),
        "pareto_candidates": summary["pareto_candidates"],
    }]

    sources = [
        {"id": "v2_summary", "label": "V2 screening summary (SQL source map)", "path": "queries/v2_report_sources.sql"},
        {"id": "v2_candidates", "label": "V2 full candidate sweep (SQL source map)", "path": "queries/v2_report_sources.sql"},
        {"id": "v2_code", "label": "V2 structural design rules (SQL source map)", "path": "queries/v2_report_sources.sql"},
        {"id": "v1_summary", "label": "V1 behavioral screening baseline", "path": "results/summary.json"},
        {"id": "park_7t2c", "label": "Park et al. a-IGZO 7T2C reference", "href": "https://link.springer.com/article/10.1007/s44469-025-00003-4"},
    ]

    cards = [
        {"id": "structural_card", "description": "进入静态拓扑审计的候选电路族。", "dataset": "report_summary", "sourceId": "v2_code", "metrics": [{"label": "结构族", "field": "structural_families", "format": "number"}]},
        {"id": "raw_card", "description": "幸存结构内的电容、工艺角色与时序笛卡尔积。", "dataset": "report_summary", "sourceId": "v2_candidates", "metrics": [{"label": "参数—时序组合", "field": "raw_candidates", "format": "number"}]},
        {"id": "pass_card", "description": "同时通过所有硬门的组合。", "dataset": "report_summary", "sourceId": "v2_candidates", "metrics": [{"label": "通过组合", "field": "functional_candidates", "format": "number"}, {"label": "通过率", "field": "pass_rate", "format": "percent"}]},
        {"id": "pareto_card", "description": "稳定性、保持、地址时间与电容面积互不支配。", "dataset": "report_summary", "sourceId": "v2_summary", "metrics": [{"label": "Pareto 组合", "field": "pareto_candidates", "format": "number"}]},
    ]

    charts = [{
        "id": "cap_tradeoff",
        "title": "通过电容组合的压缩比与源极稳定性",
        "subtitle": "9 个通过的 CST/CDATA 组合；纵轴越低表示写入后 VGS 越稳定。",
        "intent": "relationship",
        "question": "电容比如何同时影响 DATA 压缩和源极自举？",
        "rationale": "每个点是一个可制造电容组合，散点图同时保留压缩比、稳定性、CST 分组和候选身份。",
        "type": "scatter",
        "dataset": "cap_pairs",
        "sourceId": "v2_candidates",
        "encodings": {
            "x": {"field": "compression_ratio", "type": "quantitative", "label": "压缩比 κ"},
            "y": {"field": "vgs_source_sensitivity_pct", "type": "quantitative", "label": "|ΔVGS/ΔVS| (%)"},
            "color": {"field": "c_st_group", "type": "nominal", "label": "CST"},
            "label": {"field": "cap_pair", "type": "nominal", "label": "CST/CDATA (fF)"},
            "tooltip": [
                {"field": "cap_pair", "type": "nominal", "label": "CST/CDATA (fF)"},
                {"field": "total_cap_ff", "type": "quantitative", "label": "总电容 (fF)"},
                {"field": "passing_combinations", "type": "quantitative", "label": "通过组合数"},
                {"field": "best_score", "type": "quantitative", "label": "最佳评分"},
            ],
        },
        "xAxisTitle": "压缩比 κ",
        "yAxisTitle": "VGS 源极敏感度 (%)",
        "valueFormat": "number",
        "palette": {"kind": "categorical", "name": "technical-blue-orange"},
        "legend": {"position": "bottom", "sort": "labelAsc", "title": "CST"},
        "labels": {"values": "direct"},
        "layout": "full",
    }]
    # Tooltip context not otherwise needed by the visible axes.
    for row in cap_pairs:
        row["total_cap_ff"] = row["c_st_ff"] + row["c_data_ff"]

    def columns(*specs: tuple[str, str, str, str | None]) -> list[dict]:
        output = []
        for field, label, kind, unit in specs:
            item = {"field": field, "label": label}
            if kind:
                item["format" if kind in {"number", "percent"} else "type"] = kind
            if unit:
                item["unit"] = unit
            output.append(item)
        return output

    tables = [
        {"id": "funnel", "title": "顺序硬约束筛选漏斗", "subtitle": "每一行以前一行的剩余集合为分母；失败原因不是非互斥计数。", "dataset": "funnel", "sourceId": "v2_candidates", "defaultSort": {"field": "stage", "direction": "asc"}, "layout": "full", "columns": columns(("stage", "阶段", "text", None), ("remaining", "剩余", "number", None), ("removed_at_stage", "本层淘汰", "number", None), ("retention_pct", "累计保留", "number", "%"))},
        {"id": "hard_filters", "title": "V2 硬约束定义", "subtitle": "所有门槛均在排序前执行；评分不能挽救硬约束失败。", "dataset": "hard_filters", "sourceId": "v2_code", "defaultSort": {"field": "category", "direction": "asc"}, "layout": "full", "columns": columns(("category", "类别", "text", None), ("criterion", "判定量", "text", None), ("threshold", "门槛", "text", None), ("purpose", "物理目的", "text", None))},
        {"id": "circuit_families", "title": "候选电路族与静态审计结论", "subtitle": "F1/F2 进入参数阶段；其余结构在电气仿真前被规则淘汰。", "dataset": "circuit_families", "sourceId": "v2_code", "defaultSort": {"field": "family", "direction": "asc"}, "layout": "full", "columns": columns(("family", "电路族", "text", None), ("T/C", "规模", "text", None), ("controls", "GOA 组数", "number", None), ("storage", "存储结构", "text", None), ("data_path", "数据路径", "text", None), ("status", "结论", "text", None), ("reason", "原因", "text", None))},
        {"id": "netlist", "title": "F1/F2 候选原理图的连接等价表", "subtitle": "F2 只把 F1 的双脉冲 T_SCLAMP 拆成两个阶段专用 SWT。", "dataset": "netlist", "sourceId": "v2_code", "defaultSort": {"field": "device", "direction": "asc"}, "layout": "full", "columns": columns(("family", "电路族", "text", None), ("device", "器件", "text", None), ("connection", "连接", "text", None), ("control", "控制", "text", None), ("recommended_tech", "建议工艺/值", "text", None))},
        {"id": "control_timing", "title": "候选电路控制状态", "subtitle": "顺序为 RESET / COMP / SOURCE_PREP / WRITE / EMIT；F1 使用4组，F2使用5组。", "dataset": "control_timing", "sourceId": "v2_code", "defaultSort": {"field": "signal", "direction": "asc"}, "layout": "full", "columns": columns(("signal", "信号", "text", None), ("reset", "Reset", "number", None), ("comp", "Comp", "number", None), ("source_prep", "Source Prep", "number", None), ("write", "Write", "number", None), ("emit", "Emit", "number", None), ("devices", "受控器件", "text", None))},
        {"id": "cap_pairs", "title": "9 组通过的电容候选", "subtitle": "每组保留其最高评分工艺/时序；通过组合数包含工艺角色与时序变体。", "dataset": "cap_pairs", "sourceId": "v2_candidates", "defaultSort": {"field": "vgs_source_sensitivity_pct", "direction": "asc"}, "layout": "full", "columns": columns(("cap_pair", "CST/CDATA", "text", None), ("compression_ratio", "κ", "number", None), ("vgs_source_sensitivity_pct", "|ΔVGS/ΔVS|", "number", "%"), ("hold_droop_pct", "60 Hz 保持跌落", "number", "%"), ("best_address_us", "最短地址时间", "number", "µs"), ("passing_combinations", "通过组合", "number", None), ("pareto_cap_pair", "含 Pareto 点", "text", None), ("best_score", "最佳评分", "number", None))},
        {"id": "timings", "title": "通过时序候选 Top 12", "subtitle": "Timing 字段依次为 Reset/Comp/Source Prep/Write/Dead，单位 µs。", "dataset": "timings", "sourceId": "v2_candidates", "defaultSort": {"field": "best_score", "direction": "desc"}, "layout": "full", "columns": columns(("timing", "Timing", "text", None), ("address_us", "地址时间", "number", "µs"), ("passing_combinations", "通过组合", "number", None), ("best_cap_pair", "最佳 CST/CDATA", "text", None), ("best_score", "最佳评分", "number", None), ("best_candidate", "代表候选", "text", None))},
        {"id": "near_miss", "title": "补偿时间近失候选", "subtitle": "固定 160/80 fF 与最高分工艺角色，只改变补偿时间。", "dataset": "near_miss", "sourceId": "v2_candidates", "defaultSort": {"field": "comp_us", "direction": "asc"}, "layout": "full", "columns": columns(("candidate", "候选", "text", None), ("comp_us", "Comp", "number", "µs"), ("address_us", "地址时间", "number", "µs"), ("comp_settling_pct", "补偿建立率", "number", "%"), ("gap_to_98pp", "距 98% 门槛", "number", "pp"), ("decision", "结论", "text", None))},
        {"id": "technologies", "title": "SWT 工艺角色候选", "subtitle": "策略集合可重叠，用于判断哪些节点必须优先低漏电。", "dataset": "technologies", "sourceId": "v2_candidates", "defaultSort": {"field": "passing", "direction": "desc"}, "layout": "full", "columns": columns(("strategy", "策略", "text", None), ("evaluated", "评估", "number", None), ("passing", "通过", "number", None), ("pass_rate_pct", "通过率", "number", "%"), ("best_hold_droop_pct", "最佳保持跌落", "number", "%"), ("best_em_drop_mv", "最佳 EM 压降", "number", "mV"), ("interpretation", "解释", "text", None))},
        {"id": "top10", "title": "评分 Top 10 原始组合", "subtitle": "评分目标含 κ≈1/3；Top 10 接近重复是有限网格的真实结果。", "dataset": "top10", "sourceId": "v2_summary", "defaultSort": {"field": "rank", "direction": "asc"}, "layout": "full", "columns": columns(("rank", "Rank", "number", None), ("candidate", "候选", "text", None), ("caps_ff", "CST/CDATA", "text", None), ("switch_mix", "GREF/XREF/SCLAMP/DATA/EM", "text", None), ("timing_us", "R/C/P/W/D", "text", None), ("address_us", "地址时间", "number", "µs"), ("compression_ratio", "κ", "number", None), ("vgs_source_sensitivity_pct", "源极敏感度", "number", "%"), ("hold_droop_pct", "保持跌落", "number", "%"), ("score", "评分", "number", None), ("pareto", "Pareto", "text", None))},
        {"id": "robustness", "title": "电容失配与寄生角点", "subtitle": "两组候选各跑16个电容/寄生组合，不包含器件模型 PVT。", "dataset": "robustness", "sourceId": "v2_summary", "defaultSort": {"field": "worst_sensitivity_pct", "direction": "asc"}, "layout": "full", "columns": columns(("candidate", "候选", "text", None), ("nominal_kappa", "标称 κ", "number", None), ("corner_kappa", "角点 κ 范围", "text", None), ("nominal_sensitivity_pct", "标称敏感度", "number", "%"), ("worst_sensitivity_pct", "最坏敏感度", "number", "%"), ("corner_definition", "角点定义", "text", None))},
    ]

    blocks = [
        {"id": "title", "type": "markdown", "body": "# IGZO DTFT AMOLED 像素电路 V2 紧约束筛选"},
        {"id": "technical_summary", "type": "markdown", "sourceId": "v2_summary", "body": "## 结论：新稳定性约束改变了获胜结构，但尚未解决行时间\n\n旧版串联双电容 7T2C 的源极扰动代理为 **11.67%**，不能通过新的 5% 硬门。V2 要求主存储电容直接跨接 DTFT 的 G–S，并用第二只电容从独立 X 节点向 G 压缩写入。最低实现是 **6T2C/4 控制组**；若不接受双脉冲 SCAN_S，可拆为 **7T2C/5 控制组**。\n\n在 82,944 个有限组合中，2,088 个通过全部硬约束。稳定性优先电容为 **160/60 fF**（κ=0.269，源极敏感度 2.992%）；若 κ 目标取 1/3，则为 **160/80 fF**（κ=0.329，敏感度 3.002%）。当前代理下全部通过点都需要 64 µs 补偿，因此结构方向可保留，但时序尚不适合直接冻结为 GOA 规格。"},
        {"id": "metrics", "type": "metric-strip", "cardIds": ["structural_card", "raw_card", "pass_card", "pareto_card"]},
        {"id": "process_heading", "type": "markdown", "sourceId": "v2_code", "body": "## 82,944 个组合如何产生并被逐层筛掉\n\n结构层先审计 5 个电路族，仅 F1/F2 的直接 G–S 存储结构进入参数层。参数层完整交叉 6 个 CST、6 个 CDATA、5 个 SWT 角色的 32 种 IGZO/LTPS 分配，以及 72 组时序：`6×6×32×72=82,944`。硬门顺序执行，只有全部通过的组合才进入 Pareto 和加权评分。"},
        {"id": "funnel_block", "type": "table", "tableId": "funnel", "layout": "full"},
        {"id": "hard_filter_block", "type": "table", "tableId": "hard_filters", "layout": "full"},
        {"id": "circuit_heading", "type": "markdown", "sourceId": "v2_code", "body": "## 候选电路不止一个：F1 最省晶体管，F2 最省 GOA 波形复杂度\n\nF1 与 F2 使用同一电容网络和工作原理。F1 用一只源极钳位 SWT 承担 Reset 与 Source Prep/Write，因此只有4组控制，但 SCAN_S 必须输出两段脉冲；F2 将其拆成两只 SWT，用满5组控制换取每组单一连续脉冲。F3–F5 分别因源极自举不足、数据增益消失或阶段不可独立而在静态审计中淘汰。"},
        {"id": "circuit_table_block", "type": "table", "tableId": "circuit_families", "layout": "full"},
        {"id": "netlist_block", "type": "table", "tableId": "netlist", "layout": "full"},
        {"id": "control_heading", "type": "markdown", "sourceId": "v2_code", "body": "## 时序增加 SOURCE_PREP，避免把源极切换误写进 DATA 增益\n\nComp 结束后先关闭 G/X 参考开关，再在 SOURCE_PREP 固定 S。WRITE 只驱动 X，得到 `ΔVGS=κ·ΔVDATA`；DATA 与源极钳位关闭后才打开 EM。这个顺序把阈值采样、源极重定位、数据写入和发光四种电气动作分开。"},
        {"id": "control_block", "type": "table", "tableId": "control_timing", "layout": "full"},
        {"id": "model_heading", "type": "markdown", "sourceId": "v2_code", "body": "## 两个方程直接决定压缩比与写后稳定性\n\n当 S 被钳位、X 由 DATA 驱动时，`κ = CDATA/(CST+CDATA+CG,par)`。写入结束后 X 浮置，G/X 两个浮动节点按电荷守恒求解 `βS=ΔVG/ΔVS`，VGS 的残余源极敏感度为 `|1−βS|`。因此增大 CST 可以改善稳定性，但会增加面积并减慢阈值补偿；若不设置总电容上限，“稳定性最好”会退化为无限增大 CST 的无界解。\n\nRC 建立、60 Hz时保持跌落和 EM 压降使用显式代理参数；它们负责候选排序和拒绝明显差解，不等同于 PDK SPICE。"},
        {"id": "tradeoff_heading", "type": "markdown", "sourceId": "v2_candidates", "body": "## 9 组电容通过硬门；160/60 与 160/80 对应两种决策\n\n散点横轴是 DATA 压缩比，纵轴是源极每变化 1 V 时 VGS 的残余变化百分比。160/60 fF 在当前离散网格上同时给出最低敏感度和较小总电容；160/80 fF 用额外20 fF 把 κ 从0.269推到0.329，适合压缩目标接近1/3的情况。"},
        {"id": "tradeoff_chart_block", "type": "chart", "chartId": "cap_tradeoff", "layout": "full"},
        {"id": "cap_table_block", "type": "table", "tableId": "cap_pairs", "layout": "full"},
        {"id": "timing_heading", "type": "markdown", "sourceId": "v2_candidates", "body": "## 候选时序已经展开，但全部通过点集中在64 µs补偿\n\nTop 12 展示不同 Source Prep、Write 与 dead time，而不是只给一个最终脉宽。更快的 8/16/32 µs 补偿候选在其他条件相同的情况下分别只达到约43.6%、68.3%和89.8%的代理建立率，均未达到98%硬门。这说明当前瓶颈不是 DATA 写入，而是大 CST 下的阈值采样时间。"},
        {"id": "timing_block", "type": "table", "tableId": "timings", "layout": "full"},
        {"id": "near_miss_block", "type": "table", "tableId": "near_miss", "layout": "full"},
        {"id": "technology_heading", "type": "markdown", "sourceId": "v2_candidates", "body": "## GREF 必须优先低漏电，EM 则优先低导通电阻\n\nGREF 直接连接 G，使用 LTPS 代理参数时没有组合能通过60 Hz保持门。XREF/DATA 的漏电经过 κ²耦合，部分 LTPS 组合仍可工作；EM 不连接存储节点，使用 LTPS 可把300 nA代理压降从45 mV降至9 mV。因此当前最高分工艺角色是 GREF/XREF/DATA 使用 IGZO、EM 使用 LTPS；SCLAMP 对本代理评分近似不敏感。"},
        {"id": "technology_block", "type": "table", "tableId": "technologies", "layout": "full"},
        {"id": "top10_heading", "type": "markdown", "sourceId": "v2_summary", "body": "## 原始 Top 10 高度集中，不应误读为十个独立原理图\n\nTop 10 全部是160/80 fF核心结构，只在 SCLAMP 工艺和0.25–0.5 µs的辅助时序上变化。它们不是十个新电路，而是 κ≈1/3评分目标下的局部时序簇。为保留设计多样性，PDK 阶段应同时带入160/60、120/40和100/30 fF三个 Pareto 电容点，而不是只仿真这十行。"},
        {"id": "top10_block", "type": "table", "tableId": "top10", "layout": "full"},
        {"id": "robustness_heading", "type": "markdown", "sourceId": "v2_summary", "body": "## 电容/寄生扰动未击穿5%稳定性门，但器件PVT尚未覆盖\n\n对两组主候选施加 CST/CDATA ±10%与 G/X 节点寄生 ±50%的16角组合，最坏源极敏感度分别为4.87%和4.89%。这只验证电容网络鲁棒性；它没有覆盖 IGZO/LTPS 的 VTH、迁移率、亚阈值斜率、开关电荷注入和 OLED 动态。"},
        {"id": "robustness_block", "type": "table", "tableId": "robustness", "layout": "full"},
        {"id": "limitations", "type": "markdown", "body": "## 当前结果能决定结构方向，不能决定最终器件尺寸和 GOA 脉宽\n\n1. 82,944 是声明语法内的完整有限枚举，不是任意晶体管端口图的全部拓扑。\n2. F2 的参数指标由与 F1 等价的电容核心投影得到，新增 SWT 尚未单独做电荷注入仿真。\n3. 64 µs 补偿来自 V1 行为基线校准的 RC 代理；没有真实 IGZO 模型卡时不能当作产品规格。\n4. 压缩比目标尚未由用户规格给定，因此报告同时保留稳定性优先和 κ≈1/3两条路线。\n5. 没有搜索 DTFT/SWT W/L、控制高低电平、VREF/VINIT、电容版图寄生和 OLED 负载。"},
        {"id": "next_steps", "type": "markdown", "body": "## 下一轮先解决补偿速度，再扩大拓扑空间\n\n1. 把目标 κ、最大总电容面积和实际 1H 行时间变成硬规格。\n2. 引入 IGZO DTFT W/L 或补偿支路尺寸，使160 fF存储电容在目标行时间内达到≥98%建立率。\n3. 为 F1 与 F2 分别生成真实 HSPICE/Spectre 网表，比较双脉冲 GOA 复杂度与新增 SWT 的电荷注入。\n4. 至少送入四个差异化电容点：160/60、160/80、120/40、100/30 fF，并包含32 µs近失时序用于校准代理。\n5. 用 PDK 结果重新拟合 RC/漏电代理后再执行全量排序。"},
        {"id": "questions", "type": "markdown", "body": "## 会改变最终电路选择的三个未决参数\n\n- DATA 压缩比希望固定在多少：例如0.25、1/3还是0.5？\n- 目标面板的最大行地址时间是多少？\n- 优先选择 F1 的少一只 SWT，还是 F2 的单脉冲 GOA 控制？"},
    ]

    datasets = {
        "report_summary": report_summary,
        "funnel": funnel,
        "hard_filters": hard_filters,
        "circuit_families": circuit_families,
        "netlist": netlist,
        "control_timing": control_timing,
        "cap_pairs": cap_pairs,
        "timings": timings,
        "near_miss": near_miss,
        "technologies": technologies,
        "top10": ranked,
        "robustness": robustness,
    }
    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "IGZO DTFT AMOLED 像素电路 V2 紧约束筛选",
            "description": "结构候选、82,944组合筛选漏斗、电容与时序候选、工艺角色及鲁棒性审计。",
            "generatedAt": "2026-09-04",
            "cards": cards,
            "charts": charts,
            "tables": tables,
            "sources": sources,
            "blocks": blocks,
        },
        "snapshot": {"version": 1, "status": "ready", "generatedAt": "2026-09-04", "datasets": datasets},
        "sources": sources,
        "package_info": {"generated_by": "build_v2_detailed_report.py"},
    }
    (RESULTS / "artifact_v2.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    # A source-readable Markdown representation for repository review. The MCP artifact
    # remains the selected rendered report surface.
    md = [
        "# IGZO DTFT AMOLED 像素电路 V2 紧约束筛选",
        "",
        "## 技术摘要",
        "",
        "旧版串联双电容 7T2C 的源极扰动代理为 **11.67%**，不能通过新的 5% 硬门。"
        "V2 将主存储电容直接跨接 G–S，并用第二只电容从独立 X 节点向 G 压缩写入。"
        "最低实现是 **F1 6T2C/4 控制组**；若不接受双脉冲 SCAN_S，则采用 **F2 7T2C/5 控制组**。",
        "",
        "在声明语法内共审计5个结构族，并对幸存结构完整遍历 `6×6×32×72=82,944` 个"
        "电容—工艺角色—时序组合。2,088 个组合通过全部硬约束，12 个属于 Pareto 集。"
        "稳定性优先电容为 **160/60 fF**（κ=0.269，源极敏感度2.992%）；若κ目标接近1/3，"
        "则选 **160/80 fF**（κ=0.329，敏感度3.002%）。所有通过点均需要64 µs代理补偿，"
        "因此当前结果只支持结构选向，尚不能冻结器件尺寸或GOA脉宽。",
        "",
        "## 搜索空间与筛选方法",
        "",
        "结构层先审计5个电路族，仅F1/F2的直接G–S存储结构进入参数层。参数层遍历："
        "`CST={40,60,80,100,120,160} fF`、`CDATA={10,20,30,40,60,80} fF`、"
        "5个SWT角色各自选择IGZO/LTPS形成32种工艺分配，以及72组Reset/Comp/Source Prep/Write/Dead时序。"
        "硬门逐层执行；评分不能挽救任何硬门失败的组合。",
        "",
        "## 顺序筛选漏斗",
        "",
        *markdown_table(funnel, [("stage", "阶段"), ("remaining", "剩余"), ("removed_at_stage", "本层淘汰"), ("retention_pct", "累计保留 %")]),
        "",
        "## 硬约束",
        "",
        *markdown_table(hard_filters, [("category", "类别"), ("criterion", "判定量"), ("threshold", "门槛"), ("purpose", "目的")]),
        "",
        "## 候选电路族",
        "",
        *markdown_table(circuit_families, [("family", "电路族"), ("T/C", "规模"), ("controls", "控制组"), ("storage", "存储"), ("data_path", "数据路径"), ("status", "结论"), ("reason", "原因")]),
        "",
        "## 候选连接",
        "",
        *markdown_table(netlist, [("family", "电路族"), ("device", "器件"), ("connection", "连接"), ("control", "控制"), ("recommended_tech", "建议")]),
        "",
        "## 控制状态与工作阶段",
        "",
        "顺序为 RESET / COMP / SOURCE_PREP / WRITE / EMIT。Comp 与 Write 没有共同导通控制；"
        "F1复用一只源极钳位SWT并要求双脉冲，F2将Reset与Hold拆开以换取连续脉冲。",
        "",
        *markdown_table(control_timing, [("signal", "信号"), ("reset", "Reset"), ("comp", "Comp"), ("source_prep", "Source Prep"), ("write", "Write"), ("emit", "Emit"), ("devices", "器件")]),
        "",
        "## 行为模型与判定式",
        "",
        "当S被钳位、X由DATA驱动时，`κ=CDATA/(CST+CDATA+CG,par)`。写入结束后X浮置，"
        "G/X两个浮动节点按电荷守恒求解 `βS=ΔVG/ΔVS`，VGS残余源极敏感度为 `|1−βS|`。"
        "增大CST通常改善稳定性，但增加面积并减慢阈值补偿；所以必须同时施加240 fF总电容上限。",
        "",
        "RC建立率、60 Hz保持跌落和EM压降均为显式行为代理，用于初筛与排序，不能替代PDK级SPICE。",
        "",
        "## 候选时序",
        "",
        *markdown_table(timings, [("timing", "R/C/P/W/D (µs)"), ("address_us", "地址时间"), ("passing_combinations", "通过组合"), ("best_cap_pair", "最佳电容"), ("best_score", "最佳评分"), ("best_candidate", "代表候选")]),
        "",
        "## 补偿时间近失候选",
        "",
        *markdown_table(near_miss, [("candidate", "候选"), ("comp_us", "Comp µs"), ("comp_settling_pct", "补偿建立 %"), ("gap_to_98pp", "距门槛 pp"), ("decision", "结论")]),
        "",
        "## 通过电容候选",
        "",
        *markdown_table(cap_pairs, [("cap_pair", "CST/CDATA"), ("compression_ratio", "κ"), ("vgs_source_sensitivity_pct", "源极敏感度 %"), ("hold_droop_pct", "保持跌落 %"), ("passing_combinations", "通过组合"), ("pareto_cap_pair", "Pareto"), ("best_score", "最佳评分")]),
        "",
        "## SWT工艺角色候选",
        "",
        "GREF直接连接存储门节点，优先使用低漏电IGZO；EM不连接存储节点，LTPS的低导通电阻更有利。"
        "下表的策略集合允许重叠，用于识别工艺敏感角色，而不是互斥分组。",
        "",
        *markdown_table(technologies, [("strategy", "策略"), ("evaluated", "评估"), ("passing", "通过"), ("pass_rate_pct", "通过率 %"), ("best_hold_droop_pct", "最佳保持跌落 %"), ("best_em_drop_mv", "最佳EM压降 mV"), ("interpretation", "解释")]),
        "",
        "## 原始 Top 10",
        "",
        "Top 10 全部集中在160/80 fF核心，只在SCLAMP工艺和辅助时序上变化；"
        "这十行是局部参数簇，不是十个互不相同的原理图。PDK阶段应额外保留160/60、120/40和100/30 fF以维持设计多样性。",
        "",
        *markdown_table(ranked, [("rank", "Rank"), ("candidate", "候选"), ("caps_ff", "CST/CDATA"), ("switch_mix", "工艺角色"), ("timing_us", "R/C/P/W/D"), ("compression_ratio", "κ"), ("vgs_source_sensitivity_pct", "源极敏感度 %"), ("score", "评分")]),
        "",
        "## 电容失配与寄生角点",
        "",
        *markdown_table(robustness, [("candidate", "候选"), ("nominal_kappa", "标称κ"), ("corner_kappa", "角点κ"), ("nominal_sensitivity_pct", "标称敏感度 %"), ("worst_sensitivity_pct", "最坏敏感度 %"), ("corner_definition", "角点定义")]),
        "",
        "## 结论边界",
        "",
        "1. 82,944是声明语法内的完整有限枚举，不是任意晶体管端口图的全部拓扑。",
        "2. F2的参数指标由与F1等价的电容核心投影得到，新增SWT尚未单独评估电荷注入。",
        "3. 64 µs来自行为基线校准的RC代理；没有真实IGZO模型卡时不能当作产品规格。",
        "4. 压缩比目标尚未冻结，所以报告同时保留稳定性优先和κ≈1/3两条路线。",
        "5. 当前未搜索DTFT/SWT W/L、控制高低电平、VREF/VINIT、版图寄生和OLED负载。",
        "",
        "## 下一步",
        "",
        "1. 固定目标κ、最大总电容面积和实际1H行时间。",
        "2. 引入IGZO DTFT及补偿支路W/L，使大CST在目标行时间内达到≥98%建立率。",
        "3. 为F1/F2生成真实HSPICE/Spectre网表，比较双脉冲GOA与新增SWT电荷注入。",
        "4. 至少仿真160/60、160/80、120/40、100/30 fF，并保留32 µs近失时序校准代理。",
        "5. 用PDK仿真结果回归RC/漏电代理，再进行全量重排。",
        "",
        "## 会改变最终选择的未决参数",
        "",
        "- DATA压缩比目标：0.25、1/3还是0.5？",
        "- 目标面板最大行地址时间是多少？",
        "- 优先F1少一只SWT，还是F2单脉冲GOA？",
        "",
    ]
    (RESULTS / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    (RESULTS / "REPORT_SOURCE_NOTES.md").write_text(
        "# V2 report source notes\n\n"
        "Audience: technical. Delivery mode: MCP app report.\n\n"
        "Required-structure mapping: title → title block; technical summary → technical_summary; key findings → process/circuit/tradeoff/timing/technology sections; scope and definitions → hard filters/model; methodology → process and formulas; limitations and robustness → robustness/limitations; next steps and questions → final two blocks.\n\n"
        "Chart map: cap_tradeoff asks how capacitor ratio changes compression and source stability; scatter; x=compression_ratio, y=vgs_source_sensitivity_pct, color=CST; 9 cap-pair observations; single-root/categorical restrained palette; primary report artifact. Funnel remains a table because exact sequential counts and denominators matter more than bar length.\n",
        encoding="utf-8",
    )
    print(json.dumps({"datasets": {key: len(value) for key, value in datasets.items()}, "blocks": len(blocks), "tables": len(tables), "charts": len(charts)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
