# AMOLED IGZO 像素电路：V3 约束驱动筛选

[完整结果报告](results_v3/REPORT.md) · [Top 10](results_v3/top10.csv) · [可见对话记录](CONVERSATION.md)

V3 采用用户最后给出的四条要求：

1. DTFT 为 IGZO；最多 2 个电容、5 组 GOA 控制波形；STFT 可用 LTPS/IGZO。
2. DATA 电压变化写入 VGS 时有压缩比。
3. 阈值补偿与 DATA 写入分离。
4. 写入后优先保持 VGS 对源极变化稳定。

撤销旧版自行加入的 κ 范围、1/3 目标、5% 稳定性门限和 240 fF 总电容上限。数值采样范围是有限计算域，不是新增产品规格。

## 结果与重要更正

跨阶段电荷守恒检查发现，V2 在补偿期间将 X 接 VREF，会在后续 DATA 写入时衰减阈值补偿。**V2 的功能通过结论已撤回。** V3 将补偿期间的 X 改接源极 S，并同时检查补偿、源极重定位、写入、发光阶段的阈值传递。

| 层级 | 本轮实际完成 | 证据 |
|---|---:|---|
| 有限结构与阶段组合审计 | 3,024 个；5 个理想机制通过 | [逐项决定及淘汰原因](results_v3/structure_audit.csv) |
| 通过结构的电容参数点 | 180 个 | [参数全表](results_v3/all_candidates.csv) |
| 时长组合 | 24 组 | [全部 timing](results_v3/timings.csv) |
| 两种 6T2C 实现的降阶动态评估 | 55,296 组 | [完整动态结果](results_v3/dynamic_candidates.csv) |
| Top 10 的 ngspice 行为瞬态 | 90 次完成 | [测量](results_v3/spice_validation.csv)、[网表与日志](results_v3/spice/) |
| 工艺 PDK 仿真 | 0 次 | 未提供经校准 IGZO 模型 |

稳定性优先的有限域首选为 6T2C、4 组控制，CST/CDATA = 640/20 fF，κ ≈ 0.03017。NGspice 场景中的源极敏感度约为 0.746%–0.748%；参考补偿时间为 128 µs。低 β 场景仍有明显补偿残差，不能据此宣称产品指标达标。

Top 10 是同一优选核心的十组差异化电容—参考时序组合，**不是十种独立拓扑，也不是综合全局最优**。5 个结构实现、未入选参数、24 组时长和全部淘汰记录均保留。扩大电容边界可继续改善源极稳定性，但会拖慢补偿；缺少面积、行时间、压缩目标与误差权衡时，不能唯一确定综合最优。

## 电路与时序

![V3 核心电路及两种控制实现](results_v3/schematic.svg)

![V3 阶段控制与时序](results_v3/timing.svg)

两只功能电容分别跨 G–S 与 G–X；补偿期间 X 接 S。额外寄生是明确列出的环境假设，不作为新增功能电容。图中开关是连接关系表示；行为仿真使用电阻开关，不代表完成了 TFT 尺寸设计。

## 一键复现

要求 Python 3.10+、NumPy、Matplotlib，以及已安装且在 PATH 中的 ngspice（本轮验证版本 46）。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-plot.txt
python3 run_all.py
```

默认流程依次完成单元测试、结构/参数/时序筛选、90 次 ngspice、图与报告生成；任何步骤失败即停止。输出统一写入 `results_v3/`。

只重跑筛选，不调用求解器或重建报告：

```bash
python3 screen.py
```

模块入口仍可单独运行：`screen_v3.py`、`validate_v3_spice.py`、`build_v3_figures.py`、`plot_v3_waveforms.py`、`build_v3_report.py`。方法定义见 [DESIGN.md](DESIGN.md)。

## 模型与文献边界

本轮复用既有枚举、CSV、测试及报告框架，并用阶段电荷守恒审计替换不充分的局部检查。工作流参考 [AutoCkt](https://github.com/ksettaluri6/AutoCkt) 与 [PPAAS](https://github.com/SeunggeunKimkr/PPAAS) 的仿真闭环，但没有训练或运行它们的智能体。[a-IGZO 7T2C 论文](https://link.springer.com/article/10.1007/s44469-025-00003-4)提供分阶段分析参考，不构成本轮新电路的工艺验证。

DTFT 是未校准平方律行为源，STFT 是 Ron/Roff 代理，OLED 阳极由电压源施加扰动。未覆盖实测 TFT 非理想、OLED 电流/发光响应、W/L、版图寄生、GOA 驱动级、良率或老化。控制波形组数不等于完成 GOA 电路设计。

## 历史与对话

[历史归档说明](archive/README.md)保留 V1/V2 源码、数据与报告，仅供追溯，旧结论不得作为 V3 设计依据。仓库首页、默认程序和报告入口全部切换到 V3。可见对话正文保留，机器路径做公开化处理；旧链接按归档说明查找。
