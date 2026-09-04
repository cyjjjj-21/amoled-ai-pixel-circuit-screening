# AI 辅助 AMOLED 氧化物 TFT 像素电路初筛

本仓库整理了一次围绕“写入与阈值补偿分离 + 氧化物 D-TFT”的可复现实验：在受约束的
电路语法中枚举候选拓扑和时序，运行行为级瞬态角点仿真，并筛选拓扑—时序组合。

最新 V2 核心结果：

- 新约束要求 DATA 压缩写入、阈值补偿与写入分离、写后 `VGS` 对源极变化的敏感度不超过 5%；
- 静态审计 5 个电路族，其中直接 `G–S` 存储的 6T2C/7T2C 两族进入参数筛选；
- 完整遍历 `6×6×32×72 = 82,944` 个电容、SWT 工艺角色与时序组合；
- 2,088 个组合通过全部硬约束，12 个进入 Pareto 集；
- 稳定性优先方案为 `CST/CDATA=160/60 fF`，压缩比 0.269，源极敏感度 2.992%；
- 若压缩比目标接近 1/3，则采用 `160/80 fF`，压缩比 0.329，源极敏感度 3.002%；
- 当前所有通过点均需要 64 µs 行为代理补偿，结构方向可保留，但 GOA 脉宽尚不能冻结。

本实验属于 **pre-SPICE 初筛**，不代表工艺签核结论。绝对 OLED 电流、精确补偿时间、
器件尺寸、电荷注入和 PVT/老化仍需使用真实 a-IGZO RPI-62/Verilog-A/实测紧凑模型与版图寄生复核。

## 仓库内容

- [`CONVERSATION.md`](CONVERSATION.md)：从问题检索、方案判断、论文约束到筛选交付的完整可见对话；
- [`results_v2/REPORT.md`](results_v2/REPORT.md)：最新 V2 完整技术报告，包含筛选漏斗、电路族、时序候选和边界；
- [`results_v2/all_candidates.csv`](results_v2/all_candidates.csv)：V2 全部 82,944 个组合；
- [`results_v2/top10.json`](results_v2/top10.json)：V2 评分 Top 10；
- [`results_v2/artifact_v2.json`](results_v2/artifact_v2.json)：V2 结构化报告快照；
- [`screen_v2.py`](screen_v2.py)：V2 电荷守恒、RC、漏电代理与工艺分配枚举；
- [`build_v2_detailed_report.py`](build_v2_detailed_report.py)：从全量结果重建详细报告；
- [`queries/v2_report_sources.sql`](queries/v2_report_sources.sql)：报告筛选漏斗与结构输入的数据血缘；
- [`amoled_pixel_screening_report.html`](amoled_pixel_screening_report.html)：V1 技术报告；
- [`results/final_top10.json`](results/final_top10.json)：稳健性重排后的 Top 10；
- [`results/all_candidates.csv`](results/all_candidates.csv)：全部 960 个组合；
- [`screen.py`](screen.py)：拓扑枚举、行为级角点仿真和初筛；
- [`robustness.py`](robustness.py)：代理参数扰动审计；
- [`artifact.json`](artifact.json)：报告数据与来源清单。

## 复现

准备环境：

```bash
python3 -m pip install -r requirements.txt
```

运行初筛：

```bash
python3 screen.py
```

运行鲁棒性审计：

```bash
python3 robustness.py
```

运行 V2 紧约束筛选：

```bash
python3 screen_v2.py
```

重建 V2 详细报告：

```bash
python3 build_v2_detailed_report.py
```

运行测试：

```bash
python3 -m unittest -v
```

V1 输出写入 `results/`，V2 输出写入 `results_v2/`。运行环境需要 Python 3.10+ 与 NumPy。

## 方法来源与边界

工作流借鉴了 [PixelAI](https://sid.onlinelibrary.wiley.com/doi/abs/10.1002/sdtp.17868)
的受约束拓扑生成思想、显示电路多阶段贝叶斯时序优化，以及
[AutoCkt](https://github.com/ksettaluri6/AutoCkt) 与
[PPAAS](https://github.com/SeunggeunKimkr/PPAAS) 的“生成—仿真—筛选—Pareto”范式；
本仓库没有复制这些项目的源代码。直接像素结构参照 Park 等人的
[a-IGZO 7T2C 工作](https://link.springer.com/article/10.1007/s44469-025-00003-4)。

完整论文清单、约束来源、评分口径和 PDK 交接建议见技术报告及对话记录。
