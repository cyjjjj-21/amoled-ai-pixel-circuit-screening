#!/usr/bin/env python3
"""Build the canonical portable technical-report artifact from reviewed results."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def n(value, digits=3):
    return round(float(value), digits)


def main() -> None:
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    robust = json.loads((RESULTS / "robustness.json").read_text(encoding="utf-8"))
    rows = {r["candidate_id"]: r for r in csv.DictReader((RESULTS / "all_candidates.csv").open())}
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    top10 = []
    for rank, rr in enumerate(robust["robust_top10"], 1):
        base = rows[rr["candidate_id"]]
        top10.append(
            {
                "rank": rank,
                "candidate": rr["candidate_id"],
                "tR_us": n(base["t_reset_us"], 2),
                "tC_us": n(base["t_comp_us"], 2),
                "tW_us": n(base["t_write_us"], 2),
                "dead_CW_us": n(base["t_dead_cw_us"], 2),
                "dead_WE_us": n(base["t_dead_we_us"], 2),
                "dead_us": f"{n(base['t_dead_cw_us'], 2)}/{n(base['t_dead_we_us'], 2)}",
                "address_us": n(base["address_us"], 2),
                "proxy_rcer_pct": n(base["max_rcer_pct"], 2),
                "worst_proxy_rcer_pct": n(rr["worst_proxy_rcer_pct"], 2),
                "S_TH": n(base["s_th"], 3),
                "G_DATA": n(base["g_data"], 3),
                "robust_mean_rank": n(rr["mean_rank"], 2),
            }
        )

    functional_by_topology = {}
    best_by_topology = {}
    all_rows = list(rows.values())
    for row in all_rows:
        tid = row["topology_id"]
        if row["functional"] == "True":
            functional_by_topology[tid] = functional_by_topology.get(tid, 0) + 1
            if tid not in best_by_topology or float(row["score"]) > float(best_by_topology[tid]["score"]):
                best_by_topology[tid] = row

    topology_rows = []
    for tid, topo in summary["topologies"].items():
        best = best_by_topology.get(tid)
        topology_rows.append(
            {
                "topology": tid,
                "T_count": topo["transistor_count"],
                "bridge": topo["bridge_node"] or "none",
                "anchor_mask": topo["anchor_mask"],
                "em_mask": topo["em_mask"],
                "functional_timings": functional_by_topology.get(tid, 0),
                "best_score": n(best["score"], 2) if best else None,
                "best_proxy_rcer_pct": n(best["max_rcer_pct"], 2) if best else None,
            }
        )

    functional_scatter = [
        {
            "candidate": r["candidate_id"],
            "topology": r["topology_id"],
            "T_count": int(r["transistor_count"]),
            "address_us": n(r["address_us"], 2),
            "proxy_rcer_pct": n(r["max_rcer_pct"], 2),
            "tC_us": n(r["t_comp_us"], 2),
            "score": n(r["score"], 2),
        }
        for r in all_rows
        if r["functional"] == "True"
    ]

    elimination_rows = [
        {"reason": key, "count": value}
        for key, value in summary["elimination_reasons"].items()
        if key not in ("raw_generated", "hard_pass_nonisomorphic")
    ]
    elimination_rows.sort(key=lambda r: r["count"], reverse=True)

    sensitivity_rows = []
    for name, audit in robust["audit"].items():
        winner = audit["winner"]
        base = rows[winner["candidate_id"]]
        sensitivity_rows.append(
            {
                "scenario": name,
                "winner_topology": audit["winner_topology"],
                "tC_us": n(base["t_comp_us"], 2),
                "address_us": n(winner["address_us"], 2),
                "proxy_rcer_pct": n(winner["max_rcer_pct"], 2),
                "functional_combinations": audit["functional_combinations"],
            }
        )

    winner_topology = summary["topologies"][top10[0]["candidate"].split("+")[0]]
    netlist_rows = []
    for line in winner_topology["netlist"]:
        name, connection = line.split(":", 1)
        netlist_rows.append({"device": name, "connection_or_role": connection.strip()})

    sources = [
        {
            "id": "screening_results",
            "label": "Reproducible screening output",
            "path": "results/summary.json",
            "query": {
                "engine": "sqlite",
                "language": "sql",
                "sql": "SELECT * FROM screening_results",
                "tables_used": ["screening_results"],
                "description": "Role-grammar generation, structural filtering, 18-corner behavioral transient simulation and composite ranking.",
                "filters": ["5T2C–7T2C role grammar", "R→C→W→E", "write and compensation separated", "n-type oxide DRT"],
                "metric_definitions": {
                    "proxy_rcer_pct": "Maximum absolute current deviation for ΔVTH=±0.5 V relative to nominal, over three data levels and two previous-frame states; denominator floored at 50 pA.",
                    "S_TH": "Finite-difference sensitivity of stored C1 voltage to a 1 V threshold span after compensation.",
                    "G_DATA": "Finite-difference gain of emission VGS over a 5.2 V data span.",
                },
            },
        },
        {
            "id": "robustness_results",
            "label": "Nine-scenario proxy-model robustness audit",
            "path": "results/robustness.json",
            "query": {
                "engine": "sqlite",
                "language": "sql",
                "sql": "SELECT * FROM robustness_results",
                "tables_used": ["robustness_results"],
                "description": "Re-ranks all candidates under switch-speed, parasitic-capacitance, capacitor-mismatch and mobility perturbations.",
            },
        },
        {
            "id": "park_7t2c",
            "label": "Park et al., a-IGZO 7T2C pixel circuit",
            "url": "https://link.springer.com/article/10.1007/s44469-025-00003-4",
            "query": {"engine": "document", "description": "Open-access article, circuit, timing, model parameters and measured/simulated compensation results."},
        },
        {
            "id": "autockt",
            "label": "AutoCkt open-source simulator-in-the-loop workflow",
            "url": "https://github.com/ksettaluri6/AutoCkt",
            "query": {"engine": "github", "description": "Open-source analog-circuit optimization environment using generated specs, netlist simulation and rewards."},
        },
        {
            "id": "ppaas",
            "label": "PPAAS open-source analog sizing workflow",
            "url": "https://github.com/SeunggeunKimkr/PPAAS",
            "query": {"engine": "github", "description": "Open-source Pareto-oriented analog sizing workflow used as architectural reference."},
        },
    ]

    cards = [
        {"id": "raw_topologies", "description": "角色级拓扑笛卡尔积。", "dataset": "summary", "sourceId": "screening_results", "metrics": [{"label": "原始拓扑", "field": "raw_topologies", "format": "number"}]},
        {"id": "survivor_topologies", "description": "硬约束及 A/B 节点同构去重后的拓扑。", "dataset": "summary", "sourceId": "screening_results", "metrics": [{"label": "非同构幸存拓扑", "field": "survivor_topologies", "format": "number"}]},
        {"id": "sim_combinations", "description": "拓扑与离散时序的组合数。", "dataset": "summary", "sourceId": "screening_results", "metrics": [{"label": "已仿真组合", "field": "sim_combinations", "format": "number"}]},
        {"id": "transient_runs", "description": "每个组合覆盖 18 个 ΔVTH×数据×前帧角点。", "dataset": "summary", "sourceId": "screening_results", "metrics": [{"label": "瞬态角点运行", "field": "transient_runs", "format": "number"}]},
        {"id": "functional", "description": "通过单调性、驱动能力、保持、关断和灵敏度门槛的组合。", "dataset": "summary", "sourceId": "screening_results", "metrics": [{"label": "功能通过组合", "field": "functional", "format": "number"}]},
    ]

    tables = [
        {
            "id": "top10",
            "title": "稳健 Top 10 拓扑—时序组合",
            "subtitle": "按九种代理参数场景的平均名次排序；RCER 均为行为模型代理值。",
            "dataset": "top10",
            "sourceId": "robustness_results",
            "defaultSort": {"field": "rank", "direction": "asc"},
            "layout": "full",
            "columns": [
                {"field": "rank", "label": "Rank", "format": "number"},
                {"field": "candidate", "label": "组合 ID", "type": "text"},
                {"field": "tR_us", "label": "tR", "format": "number", "unit": "µs"},
                {"field": "tC_us", "label": "tC", "format": "number", "unit": "µs"},
                {"field": "tW_us", "label": "tW", "format": "number", "unit": "µs"},
                {"field": "dead_us", "label": "dead C→W/W→E (µs)", "type": "text"},
                {"field": "address_us", "label": "地址时间", "format": "number", "unit": "µs"},
                {"field": "proxy_rcer_pct", "label": "基准代理 RCER", "format": "number", "unit": "%"},
                {"field": "worst_proxy_rcer_pct", "label": "扰动最坏代理 RCER", "format": "number", "unit": "%"},
            ],
        },
        {
            "id": "netlist",
            "title": "获胜拓扑 PX-7A2E8337 的连接表",
            "subtitle": "这是原理图的可机读等价表示；节点 A/B 为两只电容的中间与远端节点。",
            "dataset": "netlist",
            "sourceId": "screening_results",
            "defaultSort": {"field": "device", "direction": "asc"},
            "layout": "full",
            "columns": [
                {"field": "device", "label": "器件", "type": "text"},
                {"field": "connection_or_role", "label": "连接 / 控制", "type": "text"},
            ],
        },
        {
            "id": "masks",
            "title": "固定四相控制掩码",
            "subtitle": "1 表示该相导通；四位依次为 Reset / Compensation / Write / Emission。",
            "dataset": "masks",
            "sourceId": "screening_results",
            "defaultSort": {"field": "order", "direction": "asc"},
            "columns": [
                {"field": "order", "label": "#", "format": "number"},
                {"field": "signal", "label": "信号", "type": "text"},
                {"field": "mask", "label": "R/C/W/E", "type": "text"},
                {"field": "devices", "label": "控制器件", "type": "text"},
            ],
        },
        {
            "id": "topology_audit",
            "title": "8 个非同构拓扑的功能筛选",
            "subtitle": "只有带 B→OLED 发光耦合且初始化覆盖写入相的 7T2C 变体形成有效簇。",
            "dataset": "topology_audit",
            "sourceId": "screening_results",
            "defaultSort": {"field": "best_score", "direction": "desc"},
            "columns": [
                {"field": "topology", "label": "拓扑 ID", "type": "text"},
                {"field": "T_count", "label": "T 数", "format": "number"},
                {"field": "bridge", "label": "发光耦合节点", "type": "text"},
                {"field": "functional_timings", "label": "功能通过时序", "format": "number"},
                {"field": "best_score", "label": "最佳分数", "format": "number"},
                {"field": "best_proxy_rcer_pct", "label": "最佳代理 RCER", "format": "number", "unit": "%"},
            ],
        },
        {
            "id": "eliminations",
            "title": "拓扑硬筛淘汰原因",
            "dataset": "eliminations",
            "sourceId": "screening_results",
            "defaultSort": {"field": "count", "direction": "desc"},
            "columns": [
                {"field": "reason", "label": "原因", "type": "text"},
                {"field": "count", "label": "数量", "format": "number"},
            ],
        },
        {
            "id": "sensitivity",
            "title": "九种代理参数场景的获胜点",
            "subtitle": "拓扑不变，但补偿时间会在 8–16 µs 之间移动。",
            "dataset": "sensitivity",
            "sourceId": "robustness_results",
            "defaultSort": {"field": "scenario", "direction": "asc"},
            "layout": "full",
            "columns": [
                {"field": "scenario", "label": "场景", "type": "text"},
                {"field": "winner_topology", "label": "获胜拓扑", "type": "text"},
                {"field": "tC_us", "label": "tC", "format": "number", "unit": "µs"},
                {"field": "address_us", "label": "地址时间", "format": "number", "unit": "µs"},
                {"field": "proxy_rcer_pct", "label": "代理 RCER", "format": "number", "unit": "%"},
            ],
        },
    ]

    charts = [
        {
            "id": "speed_error_tradeoff",
            "title": "地址时间与阈值偏移代理误差",
            "subtitle": "120 个功能通过组合；每点为一个拓扑—时序组合，颜色区分拓扑。",
            "intent": "relationship",
            "question": "更短的地址时间需要付出多大的阈值偏移代理误差代价？",
            "rationale": "散点图保留每个候选的同粒度地址时间与误差，能显示 8 µs 和 16 µs 补偿簇以及两个功能拓扑的分离。",
            "type": "scatter",
            "dataset": "functional_scatter",
            "sourceId": "screening_results",
            "encodings": {
                "x": {"field": "address_us", "type": "quantitative", "label": "地址时间 (µs)"},
                "y": {"field": "proxy_rcer_pct", "type": "quantitative", "label": "最大代理 RCER (%)"},
                "color": {"field": "topology", "type": "nominal", "label": "拓扑"},
                "label": {"field": "candidate", "type": "nominal", "label": "组合 ID"},
                "tooltip": [
                    {"field": "candidate", "type": "nominal", "label": "组合 ID"},
                    {"field": "tC_us", "type": "quantitative", "label": "补偿时间 (µs)"},
                    {"field": "score", "type": "quantitative", "label": "基准分数"},
                ],
            },
            "xAxisTitle": "地址时间 (µs)",
            "yAxisTitle": "最大代理 RCER (%)",
            "valueFormat": "number",
            "palette": {"kind": "categorical", "name": "technical-blue-orange"},
            "legend": {"position": "bottom", "sort": "labelAsc", "title": "拓扑"},
            "labels": {"values": "none"},
            "layout": "full",
        }
    ]

    blocks = [
        {"id": "title", "type": "markdown", "body": "# 氧化物 AMOLED 像素电路初筛"},
        {
            "id": "technical_summary",
            "type": "markdown",
            "sourceId": "screening_results",
            "body": "## 结论：先推进受保护双电容 7T2C，6T2C 暂不进入 PDK 仿真\n\n在限定的角色级搜索语法中，**PX-7A2E8337** 是唯一形成高质量功能簇的拓扑：C1 跨接 DRT 栅极 G 与节点 A 保存阈值，C2 跨接 A 与 B 保存数据；发光阶段由 T4 将 DRT 源极接 OLED、T6 将 B 接 OLED，从而让发光开关与 C1 间接耦合。基准稳健首选时序为 **0.5 / 16 / 0.5 µs**（R/C/W），两段 dead time 均为 **0.05 µs**，地址时间 **17.1 µs**。其行为模型代理 RCER 为 **13.35%**，九种参数扰动下最坏为 **14.57%**。\n\n这不是工艺级电流预测。结论的可信层级是：**拓扑优先级较稳，精确时序与电流数值尚未定型**。下一步应只把该 7T2C 及 8 µs/16 µs 两个补偿时间簇送入真实 a-IGZO 紧凑模型。",
        },
        {"id": "metrics", "type": "metric-strip", "cardIds": [c["id"] for c in cards]},
        {"id": "tradeoff_chart", "type": "chart", "chartId": "speed_error_tradeoff", "layout": "full"},
        {
            "id": "key_finding",
            "type": "markdown",
            "sourceId": "robustness_results",
            "body": "## Top 10 不是十个不同原理图，而是一个稳定拓扑的十组时序\n\n硬约束把大多数接法直接排除；余下 8 个非同构候选中，仅两个 7T2C 控制变体通过功能门槛，而 Top 20 在全部九种参数场景中都由 PX-7A2E8337 占据。为了避免虚构拓扑多样性，下面保留真实的“拓扑 × 时序”排名。第 8、10 名是 **8 µs compensation** 高速候选，适合与 **16 µs** 稳态候选共同进入下一轮。",
        },
        {"id": "top10_block", "type": "table", "tableId": "top10", "layout": "full"},
        {
            "id": "winner_structure",
            "type": "markdown",
            "sourceId": "park_7t2c",
            "body": "## 获胜结构与公开论文的 7T2C 同构\n\n连接关系与 Park 等人的 a-IGZO 7T2C 一致：T1/T2 在补偿相结束后关闭，T3/T5 完成数据写入，T4/T6 仅在 Reset 与 Emission 导通。论文给出 C1=C2=40 fF、VDD=8.5 V、VREF=2 V，并用测量拟合的 RPI level-62 模型做 HSPICE 验证；其仿真最大 RCER 为 10.07%，五个实测电路最大为 14.99%。本报告只复用其公开参数作为行为模型锚点，不复用未公开的模型卡。",
        },
        {"id": "netlist_block", "type": "table", "tableId": "netlist", "layout": "full"},
        {"id": "masks_block", "type": "table", "tableId": "masks"},
        {
            "id": "scope",
            "type": "markdown",
            "body": "## 搜索空间只覆盖当前问题，不覆盖整个 AMOLED 像素宇宙\n\n**包含：** n 型氧化物 DRT、电压编程、Reset→Compensation→Write→Emission、写入与补偿分离、恰好 2C、总计 6T2C 或 7T2C、最多 4 条控制线、单 VREF/VDATA、break-before-make、±0.5 V DRT 阈值偏移。\n\n**排除：** 电流编程、外部感测、迁移率/OLED 老化/IR-drop 联合补偿、双栅、互补 TFT、多级电压、邻行信号、超过 7T/2C、尺寸和拓扑联合搜索、GOA 联合优化。这里的“全部拓扑”只指上述角色语法内的完整枚举，不指任意晶体管端口图。",
        },
        {
            "id": "method",
            "type": "markdown",
            "sourceId": "screening_results",
            "body": "## 两级方法：先证明图合法，再做 18 角行为瞬态\n\n第一层生成 288 个角色级接法，执行电流路径、两电容职责、补偿路径、数据唯一入口、OLED 地址期关断、控制掩码、C1 发光期隔离和 A/B 同构去重。第二层将 8 个非同构拓扑与 120 组离散时序交叉，覆盖 ΔVTH={−0.5,0,+0.5 V}、VDATA={−0.2,2.4,5 V}、前帧={低,高} 的 18 个角点。\n\n节点方程采用电容 MNA、有限导通/关断电导、平方律加亚阈值 DRT 代理和 OLED 负载。综合分数权重为：代理 RCER 30%、阈值存储灵敏度 16%、数据增益 14%、前帧独立性 14%、非发光漏电 10%、地址速度 10%、晶体管数 6%。AutoCkt 的 simulator-in-the-loop 分层与 PPAAS 的 Pareto 思路被用于流程设计，但两者的硅 MOS 网表和模型未直接套用。",
        },
        {"id": "topology_block", "type": "table", "tableId": "topology_audit", "layout": "full"},
        {"id": "elimination_block", "type": "table", "tableId": "eliminations"},
        {
            "id": "robustness",
            "type": "markdown",
            "sourceId": "robustness_results",
            "body": "## 拓扑结论稳定，时序结论对寄生和迁移率敏感\n\n九种代理参数场景均选择 PX-7A2E8337；这支持先固定拓扑、再用真实模型优化时序。寄生翻倍、C1−10%/C2+10% 或迁移率+20% 时，8 µs 补偿点可超越 16 µs 点，说明当前 16 µs 最优值不能直接转成 GOA 脉宽规格。稳健名单因此同时保留两类补偿时间。",
        },
        {"id": "sensitivity_block", "type": "table", "tableId": "sensitivity", "layout": "full"},
        {
            "id": "limitations",
            "type": "markdown",
            "body": "## 最大不确定性来自缺失的 a-IGZO 模型卡与版图寄生\n\n1. 代理模型不含 RPI-62 的陷阱态、接触、偏压应力、温度和历史依赖，代理 RCER 不能当作签核指标。\n2. 开关 kickback 只通过结构隔离与集中寄生近似，没有每只 SWT 的 Cgd/Cgs 和时钟摆幅注入。\n3. OLED 低灰动态用串联稳态电流近似，未跑完整 120 Hz 帧长充放电。\n4. 未联合搜索 W/L、C1/C2、VREF、控制电平和 GOA 负载；当前绝对电流只用于单调性与相对比较。\n5. 未制作排名柱图：十个综合分数高度接近，且综合分数是人为加权序数；精确表格比视觉长度更不容易制造虚假差异。",
        },
        {
            "id": "next_steps",
            "type": "markdown",
            "body": "## 下一步：只为一个拓扑准备工艺级仿真包\n\n1. 获取或拟合 a-IGZO RPI-62 / Verilog-A 模型（至少 Id–Vg、Id–Vd、SS、Cgd/Cgs、温度与 ΔVTH）。\n2. 将 PX-7A2E8337 生成为 HSPICE/Spectre 网表，先跑 Top 1、Top 8 两个代表时序，再扩展 Top 10。\n3. 把 C1/C2、各 SWT W/L、VREF、VGL/VGH 和 1H 上限加入连续优化；约束低灰 RCER、写入 settling、OLED off-current 和电压应力。\n4. 在寄生提取后重新执行 18 角，并增加温度、SWT 阈值、OLED 老化、VDD IR-drop 与长帧保持。\n5. 只有在 7T2C 无法满足面积/线数目标时，才放宽“发光期 C1 间接耦合”或 2C/7T 上限重新搜索。",
        },
        {
            "id": "questions",
            "type": "markdown",
            "body": "## 进入第二轮前仍需回答\n\n- 目标面板分辨率、刷新率和实际 1H 上限是多少？\n- DRT/SWT 是否共用同一 a-IGZO 模型与阈值分布？\n- 低灰目标电流、允许 RCER、OLED 电容和阳极初始电压是多少？\n- 允许几条独立 GOA 信号线，EM 是否可在 Reset 同时拉高？\n- 面积目标更偏向 6T2C，还是可接受 7T2C 换取低灰稳定性？",
        },
        {
            "id": "sources_note",
            "type": "markdown",
            "body": "## 公开依据\n\n- [Park et al., a-IGZO 7T2C circuit and timing](https://link.springer.com/article/10.1007/s44469-025-00003-4)\n- [AutoCkt: Deep reinforcement learning of analog circuit designs](https://github.com/ksettaluri6/AutoCkt)\n- [PPAAS: open-source analog sizing workflow](https://github.com/SeunggeunKimkr/PPAAS)\n- [5T2C oxide-pixel comparison reference](https://www.mdpi.com/2072-666X/14/4/857)\n\n所有本地结果均可由 `screen.py` 与 `robustness.py` 重现。",
        },
    ]

    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "氧化物 AMOLED 像素电路初筛",
            "description": "Constraint-first behavioral pre-SPICE screen for a-IGZO AMOLED pixel topology and timing combinations.",
            "generatedAt": generated,
            "cards": cards,
            "charts": charts,
            "tables": tables,
            "sources": [{k: v for k, v in s.items() if k in ("id", "label", "path", "url")} for s in sources],
            "blocks": blocks,
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated,
            "status": "ready",
            "datasets": {
                "summary": [{
                    "raw_topologies": summary["raw_topologies"],
                    "survivor_topologies": summary["hard_pass_nonisomorphic_topologies"],
                    "sim_combinations": summary["simulated_combinations"],
                    "transient_runs": summary["total_transient_runs"],
                    "functional": summary["functional_combinations"],
                }],
                "top10": top10,
                "functional_scatter": functional_scatter,
                "netlist": netlist_rows,
                "masks": [
                    {"order": 1, "signal": "SCAN1", "mask": "1100", "devices": "T1_REF, T2_COMP"},
                    {"order": 2, "signal": "SCAN2", "mask": "0010", "devices": "T3_DATA"},
                    {"order": 3, "signal": "SCAN3", "mask": "1110", "devices": "T5_INIT"},
                    {"order": 4, "signal": "EM", "mask": "1001", "devices": "T4_EM, T6_EM_COUPLE"},
                ],
                "topology_audit": topology_rows,
                "eliminations": elimination_rows,
                "sensitivity": sensitivity_rows,
            },
        },
        "sources": sources,
        "package_info": {"root": "amoled-pixel-screening", "manifestPath": "artifact.json", "snapshotPath": "artifact.json"},
    }
    (ROOT / "artifact.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(ROOT / "artifact.json")


if __name__ == "__main__":
    main()
