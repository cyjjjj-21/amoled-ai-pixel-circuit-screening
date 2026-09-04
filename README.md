# AI 辅助 AMOLED 氧化物 TFT 像素电路初筛

本仓库整理了一次围绕“写入与阈值补偿分离 + 氧化物 D-TFT”的可复现实验：在受约束的
电路语法中枚举候选拓扑和时序，运行行为级瞬态角点仿真，并筛选拓扑—时序组合。

核心结果：

- 生成 288 个角色级拓扑，硬约束和同构去重后保留 8 个；
- 与 120 组时序交叉，共评估 960 个组合；
- 完成 17,280 次行为级瞬态角点运行，120 个组合通过功能门槛；
- 九种代理参数扰动下，获胜拓扑均为受保护双电容 7T2C `PX-7A2E8337`；
- 基准最佳组合的代理 RCER 为 13.35%，参数扰动最坏值为 14.57%。

本实验属于 **pre-SPICE 初筛**，不代表工艺签核结论。绝对 OLED 电流、精确补偿时间与
RCER 仍需使用真实 a-IGZO RPI-62/Verilog-A/实测紧凑模型和版图寄生复核。

## 仓库内容

- [`CONVERSATION.md`](CONVERSATION.md)：从问题检索、方案判断、论文约束到筛选交付的完整可见对话；
- [`amoled_pixel_screening_report.html`](amoled_pixel_screening_report.html)：最终技术报告；
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

运行测试：

```bash
python3 -m unittest -v
```

输出写入 `results/`。运行环境需要 Python 3.10+ 与 NumPy。

## 方法来源与边界

工作流借鉴了 [PixelAI](https://sid.onlinelibrary.wiley.com/doi/abs/10.1002/sdtp.17868)
的受约束拓扑生成思想、显示电路多阶段贝叶斯时序优化，以及
[AutoCkt](https://github.com/ksettaluri6/AutoCkt) 与
[PPAAS](https://github.com/SeunggeunKimkr/PPAAS) 的“生成—仿真—筛选—Pareto”范式；
本仓库没有复制这些项目的源代码。直接像素结构参照 Park 等人的
[a-IGZO 7T2C 工作](https://link.springer.com/article/10.1007/s44469-025-00003-4)。

完整论文清单、约束来源、评分口径和 PDK 交接建议见技术报告及对话记录。
