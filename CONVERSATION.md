# 完整对话记录

> 范围：按时间顺序收录用户与助手可见消息，包括进度更新与最终答复；
> 不包含系统/开发者指令、隐藏推理、工具原始日志和自动注入的环境信息。
> 为适合公开发布，仅将旧回复中的本机绝对路径前缀规范化为仓库相对路径，
> 其余对话正文保持不变。

## 用户 1

帮我搜索一下github上和科研论文网站，看看有没有利用ai模型来进行amoled tft像素驱动电路和goa电路设计仿真的文章或者idea

## 助手 1 · 进度更新

我先把范围拆成两条线同步检索思路：一条找直接针对 AMOLED TFT 像素驱动/GOA 的 AI 设计与仿真论文，另一条找可迁移的方法（神经网络代理模型、参数反演、贝叶斯优化、强化学习、电路生成）和可复用 GitHub 项目。最后我会区分“已有直接工作”和“值得做的研究 idea”，并给出来源链接。

## 助手 2 · 进度更新

已经找到一条非常直接的证据：2024 年 SID 的 “PixelAI” 确实用强化学习自动设计 AMOLED 像素电路；同一团队 2025 年又把深度强化学习用于像素版图面积优化。接下来重点确认两件事：是否有公开代码/学位论文细节，以及 GOA 是否已有同等级的直接 AI 工作。

## 助手 3 · 最终答复

有，而且比预想中更直接。AMOLED 像素电路已经出现强化学习拓扑生成、贝叶斯优化时序设计和强化学习版图优化；GOA 方面已有“电路仿真 + 遗传/多目标进化算法”的实测论文，但直接使用深度学习或强化学习生成 GOA 拓扑的公开工作仍很少，研究空间更大。

## 直接相关论文

| 方向 | 工作 | 方法与价值 |
|---|---|---|
| 像素电路拓扑生成 | [PixelAI: Designing AMOLED Pixel Circuits using Reinforcement Learning（SID 2024）](https://sid.onlinelibrary.wiley.com/doi/abs/10.1002/sdtp.17868) | 直接用强化学习生成 AMOLED 像素电路连接，包含连接掩码、初始节点连接、分阶段子目标、冗余电路裁剪和初始状态选择。属于最直接的“AI 设计 AMOLED 像素电路”证据。 |
| 像素输入时序设计 | [Efficient Multi-stage Bayesian Optimization for Optimal Display Circuit Input Signal Design（SID 2023）](https://sid.onlinelibrary.wiley.com/doi/10.1002/sdtp.16518) | 用多阶段贝叶斯优化自动搜索编程/发光阶段的输入电压和时序参数；在 3T1C、7T1C 上验证。特别适合扫描时间、补偿时间、EL/SCAN 波形优化。 |
| 像素版图优化 | [Layout Optimization of AMOLED Pixel Circuits based on Deep Reinforcement Learning（SID 2025）](https://sid.onlinelibrary.wiley.com/doi/abs/10.1002/sdtp.18514) | 通过器件反复重定位和连线重布，优化像素版图面积。说明同一研究路线已经从 schematic 扩展到 layout。 |
| GOA 参数优化 | [Dynamic Characteristic Optimization of 14 a-Si:H TFTs Gate Driver Circuit（JDT 2011）](https://scholar.nycu.edu.tw/en/publications/dynamic-characteristic-optimization-of-14-a-sih-tfts-gate-driver-/) | GA 与 TFT 电路仿真器闭环，优化 14 个 TFT 的宽度和无源器件；约减少 35% 总 TFT 宽度，并完成 4 μm a-Si:H 工艺流片验证。 |
| GOA 多目标优化 | [Circuit-Simulation-Based Multi-Objective Evolutionary Algorithm…（JDT 2015）](https://opg.optica.org/jdt/abstract.cfm?uri=jdt-11-8-640) | MOEA 同时优化下降时间、纹波和面积，并联合搜索多电平 clock；下降时间降低超过 50%，有实测验证。 |
| GOA 多约束优化 | [Optimal Design of a Novel Amorphous Silicon Gate Driver Circuit…（2016）](https://scholar.nycu.edu.tw/zh/publications/optimal-design-of-a-novel-amorphous-silicon-gate-driver-circuit-u/) | 对 15T2C GOA 优化 rise/fall time、ripple、clock capacitance 和总 TFT 宽度，展示了典型的多目标 GOA 自动设计流程。 |
| GOA 拓扑生成的基础 | [GateRL（2021）](https://www.mdpi.com/2079-9292/10/9/1032) | 用 DQN、连接矩阵和 action masking 从晶体管级生成逻辑门。论文明确提到该方法面向“只能使用单一类型 TFT 的面板移位寄存器”这类问题，但实验仍是 CMOS 门，不是完整 GOA。 |
| 更先进的拓扑生成基础 | [fast-GateRL（IEEE Access 2025）](https://doi.org/10.1109/ACCESS.2025.3555771) | 增加阈值电压、直通电流检查、scoreboard 中间奖励、裁剪与初始状态复用；比原 GateRL 更适合改造成 GOA 拓扑生成器。 |
| TFT 神经网络模型 | [Neural Compact Modeling Framework for a-IGZO TFT（2024）](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aisy.202300435) | 使用两阶段神经网络构建可参数化 a-IGZO TFT compact model；基于 1000 个 TCAD 器件，报告平均 \(I_{DS}\) 误差约 0.27%、DC \(R^2>0.995\)，并面向快速 SPICE 仿真。 |
| TFT 工艺/器件优化 | [Machine Learning Driven Channel Thickness Optimization…（2023）](https://advanced.onlinelibrary.wiley.com/doi/10.1002/advs.202303589) | 用 Gaussian Process + Bayesian Optimization 优化双层氧化物 TFT，在约 15 组实验数据下联合考虑迁移率和阈值电压。可作为 circuit–device co-optimization 的上游。 |

补充背景综述可看 [Review of Integrated Gate Driver Circuits in Active Matrix TFT Display Panels（2024）](https://www.mdpi.com/2072-666X/15/7/823)，里面整理了 a-Si、LTPS、oxide TFT GOA 的基本结构、预充电/自举/下拉阶段和可靠性问题，适合定义 AI 环境的规则和指标。

## GitHub 上可复用的项目

没有检索到 PixelAI、SID 2023 像素时序优化或上述 GOA 论文的官方公开代码。比较适合改造的开源框架是：

- [AutoCkt](https://github.com/ksettaluri6/AutoCkt)：论文配套的 RL + NGSpice 参数优化框架。最适合先替换 netlist、参数空间和 reward，做固定拓扑的 TFT W/L、C、时序优化。

- [PPAAS](https://github.com/SeunggeunKimkr/PPAAS)：面向 PVT 和 Pareto front 的 goal-conditioned RL。适合 AMOLED/GOA 的多 corner、多目标和不同产品规格复用。

- [AnalogGenie](https://github.com/xz-group/AnalogGenie)：把 SPICE 电路转成图/Eulerian sequence，再由 Transformer 生成拓扑。可用于像素电路或 GOA 候选拓扑预训练，但需要自己建立 TFT 电路数据集和仿真验证层。

- [GNN-ACLP](https://github.com/guanyuanpeterpan/GNN-ACLP)：利用 GNN 预测电路缺失连接。可以把 GOA 拓扑生成拆成“已有骨架 + 推荐下一条连接”，比完全从零生成更容易训练。

- [RALF](https://github.com/iic-jku/IIC-RALF)：RL 辅助模拟版图 placement/routing。器件和 PDK 当前是 SKY130，但其“SPICE 网表→器件约束识别→placement→routing”的结构可参考像素/GOA 版图自动化。

关键工程限制是：这些仓库基本面向 CMOS + NGSpice。真正落地时最好保留现有 SmartSpice/HSPICE/Spectre/TFT Verilog-A 模型，把 AI 框架只作为外层 optimizer，不要一开始强行迁移到 CMOS PDK。

## 最值得做的研究 idea

### 1. 固定拓扑的 PVT/老化鲁棒优化

最容易做出结果，风险最低。

输入：

- TFT \(W/L\)、storage/bootstrap capacitor
- SCAN/EM/CLK 电压、脉宽、重叠和延迟
- LTPS/IGZO 的 \(V_{TH}\)、mobility、leakage、寄生 RC
- OLED \(V_{TH}\) 漂移、ELVDD IR drop

目标：

- 像素：OLED 电流误差、编程时间、低灰阶误差、功耗、面积、闪烁
- GOA：rise/fall time、ripple、输出摆幅、级联传播失败率、clock loading、功耗、面积

方法建议使用 constrained multi-objective BO；比直接 RL 更省 SPICE 样本，也容易和 random search、GA、NSGA-II 做公平比较。

### 2. GOA“器件尺寸 + 多电平时钟”联合优化

把 2015 年 MOEA-GOA 工作和 2023 年像素多阶段 BO 结合起来：

- 外层搜索 TFT W/L、bootstrap C；
- 内层按 pre-charge → bootstrap → pull-down 阶段，反向优化 CLK 波形；
- 最终做 50–200 级 cascade simulation；
- 在 \(V_{TH}\) shift、温度、RC load 和 clock skew 下验证。

这是很扎实、工程价值很高、又没有明显被现代 BO/RL 充分覆盖的题目。

### 3. 基于 fast-GateRL 的单极性 TFT GOA 拓扑生成

创新性最高。

不要只给最终 pass/fail reward，而是按功能阶段提供 scoreboard：

1. Q 节点能否预充；
2. 自举后是否达到要求电压；
3. 输出能否驱动目标 RC；
4. 下拉阶段能否清零；
5. 非选通期间是否抑制噪声；
6. 多级级联是否无错误传播；
7. 加入 \(V_{TH}\) shift 后是否仍工作。

Action masking 可直接编码：

- 禁止电源短路；
- 禁止浮空关键节点；
- 限制单一 N-type 或 P-type TFT；
- 限制最大 TFT/C 数；
- 禁止 gate 无驱动；
- 限制不可制造的 clock/node 连接。

这比把 GOA 当普通模拟电路做黑箱 RL 更容易收敛。

### 4. AI surrogate 加速 Monte Carlo 和老化仿真

先用 SPICE/TCAD 生成数据，训练 GNN、MLP 或 Gaussian Process 预测完整 waveform metrics，再由 surrogate 筛掉大部分差解，只让少量候选进入真实仿真。

重点不要只预测单个标称点，而要预测：

- mean / worst-case / failure probability；
- \(V_{TH}\) shift 后的退化曲线；
- 像素电流误差分布；
- GOA 第 \(N\) 级脉冲畸变。

### 5. Pixel–GOA 协同优化

目前大部分论文把像素和 GOA 分开。可以让 GOA 输出波形作为像素电路的真实输入，共同优化：

\[
\text{GOA尺寸/时钟}\rightarrow
\text{扫描波形}\rightarrow
\text{像素编程误差}\rightarrow
\text{OLED电流与功耗}
\]

这能避免“GOA 自己指标很好，但实际像素充电和低灰阶表现不好”的局部最优，论文新颖性也更强。

## 我的判断

- “有没有”：确定有，且像素电路已经进入深度强化学习阶段。
- “GOA 有没有现代 AI 模型直接做”：公开文献中，直接 GOA 工作主要还是 GA/MOEA + TFT simulator；GateRL/fast-GateRL 提供了非常接近的深度强化学习技术基础。
- “哪个方向最适合马上启动”：优先做 GOA 或 AMOLED 固定拓扑的多目标贝叶斯优化与鲁棒 corner 优化；仿真链路跑通后，再扩展到拓扑生成。
- “最有论文差异化的方向”：单极性 TFT GOA 拓扑生成，或 Pixel–GOA 联合闭环优化。

## 用户 2

我需要基于一种基本的功能，比如“写入比补偿分离”+“氧化物dtft” 来让模型遍历所有可能的电路拓扑，所有可能的时序，完成全部前仿真，并筛选出综合性能最优的top10 电路原理图+timing的组合，你判断一下基于现有的工作哪一个可以支持？

## 助手 4 · 进度更新

我会按你的真实目标判断“能不能支撑完整流程”，不是只看论文标题。关键是同时覆盖四件事：拓扑生成、时序生成、氧化物 TFT/SPICE 前仿真、以及多目标 Top-10 排序；很可能现有单一框架都不够，需要确定最小组合。

## 助手 5 · 最终答复

结论：没有一个现成项目可以单独完成你的目标。最合适的路线是：

> PixelAI 的受约束拓扑生成思想 + 多阶段贝叶斯时序优化 + PPAAS 的多目标/PVT 排序框架 + 自研的拓扑枚举与氧化物 TFT 仿真调度器。

如果只能选一个“核心参考工作”，选 PixelAI；如果只能选一个“可改代码底座”，选 PPAAS/AutoCkt。但真正保证“遍历所有可能拓扑”的核心不能依靠 RL 或生成模型，必须由确定性的图枚举/约束求解器完成。

## 现有工作的支持程度

| 工作 | 拓扑生成 | 时序优化 | 氧化物 TFT | PVT/多目标 Top-10 | 判断 |
|---|---:|---:|---:|---:|---|
| [PixelAI](https://khu.elsevierpure.com/en/publications/pixelai-designing-amoled-pixel-circuits-using-reinforcement-learn) | 强 | 弱 | 需替换模型 | 中 | 最接近你的功能目标，但论文只有 3 页且没有检索到公开代码 |
| [Multi-stage BO for display input signals](https://www.citedrive.com/en/discovery/144-efficient-multistage-bayesian-optimization-for-optimal-display-circuit-input-signal-design/) | 无 | 很强 | 仿真器无关 | 中 | 最适合“写入、补偿分离”的时序搜索 |
| [fast-GateRL](https://doi.org/10.1109/ACCESS.2025.3555771) | 强 | 无 | 原工作是 CMOS | 弱 | 连接掩码、阶段奖励、裁剪机制很有价值 |
| [PPAAS](https://github.com/SeunggeunKimkr/PPAAS) | 无 | 可改 | 需接入 TFT simulator | 很强 | 最适合作为多目标、PVT、Pareto 排序的代码底座 |
| [AutoCkt](https://github.com/ksettaluri6/AutoCkt) | 无 | 可改 | 需替换 NGSpice 模型 | 中 | 环境简单，适合第一版原型 |
| [AnalogGenie](https://github.com/xz-group/AnalogGenie) | 可生成 | 无 | 无 | 弱 | 适合学习已有电路先验，不适合保证完整遍历 |
| GOA 的 GA/MOEA 工作 | 固定拓扑 | 参数/clock | 有 TFT simulator | 中 | 证明 simulator-in-loop 可行，但不解决拓扑生成 |

## 为什么不能让 AI 模型直接“遍历全部”

如果有 \(N\) 个 TFT，每个 TFT 有 G/S/D 三个端子，并允许连接到 \(K\) 个内部节点、电源、DATA、SCAN、EM 等信号，原始连接空间近似包含：

\[
K^{3N}
\]

种端子分配。再加上：

- 电容连接；
- 节点等价；
- TFT 源漏互换；
- 不同控制信号；
- 多个工作阶段；
- 连续的电压、脉宽、延迟；

“所有时序”本身是连续无限空间。因此需要把要求改写为：

> 完整枚举一个明确、有限的设计语法中的全部离散拓扑和离散控制状态，再对每个可行拓扑优化连续时序参数。

RL、LLM 或 Transformer 只能优先探索，不保证不漏解。要声称“全部遍历”，必须使用确定性枚举。

## 最适合你的系统结构

### 1. 先把功能写成有限电路语法

以“补偿和写入分离、氧化物 D-TFT”为基础，定义：

- 恰好一个 oxide D-TFT；
- 最多 \(N_T\) 个开关 TFT，例如 4–9 个；
- 最多 1–2 个存储电容；
- 最多 \(N_I\) 个内部节点；
- DATA、VREF、ELVDD、ELVSS；
- SCAN、COMP、WRITE、EM 等允许的控制线；
- 固定阶段顺序：初始化 → 补偿 → 写入 → 发光；
- 补偿和写入必须是两个独立状态。

如果只有 D-TFT 是氧化物，其他开关 TFT 可以单独定义器件类型；如果所有 TFT 都是 oxide，则增加“全 N 型/单极性”约束。

### 2. 用确定性拓扑枚举器保证覆盖

这部分不是 PixelAI，而是必须新增的核心。

建议使用：

- Z3/SAT：生成满足约束的端子连接；
- NetworkX/nauty：电路图 canonicalization；
- 图同构去重；
- 静态电路规则剪枝。

必须提前排除：

- 电源短路；
- DATA 直接连 OLED；
- D-TFT gate 永久浮空；
- 电容两端同节点；
- 无法初始化的存储节点；
- COMP 阶段没有阈值采样路径；
- WRITE 阶段必然破坏补偿电压；
- 发光期间 D-TFT 不在 OLED 电流路径；
- 无意义、并联重复或不可控制的 TFT。

PixelAI 的 mask matrix、sub-goal、trimming 思想正好可以用在这里，但应作为枚举剪枝和候选优先级，而不是完整性的唯一保障。[PixelAI](https://khu.elsevierpure.com/en/publications/pixelai-designing-amoled-pixel-circuits-using-reinforcement-learn)本身已经验证了 AMOLED 拓扑生成可以使用连接掩码、子目标和电路裁剪。

### 3. 离散时序也先确定性枚举

对每个阶段枚举控制信号的高低状态，例如：

| 阶段 | WRITE | COMP | EM | 功能约束 |
|---|---:|---:|---:|---|
| Init | 0/1 | 0/1 | OFF | 存储节点进入确定状态 |
| Comp | OFF | ON | OFF | D-TFT 的 \(V_{TH}\) 信息写入存储节点 |
| Write | ON | OFF | OFF | 数据写入且不能破坏补偿量 |
| Emit | OFF | OFF | ON | OLED 电流由已存储状态决定 |

这一步枚举的是逻辑状态，不是具体的脉宽和电压。

### 4. 连续时序用多阶段 BO

然后再优化：

- Init/Comp/Write 时间；
- 各阶段切换间隔；
- COMP、WRITE、SCAN 电压；
- VREF；
- EM 提前量/延迟量；
- clock overlap/non-overlap；
- DATA settling time。

这里直接采用 2023 年的多阶段贝叶斯优化思想最合适：分别优化各工作阶段，并按“发光 → 写入 → 补偿 → 初始化”的逆向顺序逐步收紧搜索空间。该方法已经在 3T1C 和 7T1C 像素电路上验证。[论文](https://www.citedrive.com/en/discovery/144-efficient-multistage-bayesian-optimization-for-optimal-display-circuit-input-signal-design/)

你的“写入和补偿分离”反而特别适合这种阶段化优化。

## 仿真筛选漏斗

不建议对原始组合直接做全部高精度 corner 仿真，会浪费绝大多数计算量。建议分四层：

1. 图级筛选  
   检查连接合法性、路径、浮空、短路、阶段可控性。

2. 快速标称仿真  
   每个拓扑只用一组典型参数，跑完整 Init/Comp/Write/Emit transient。

3. 时序优化  
   对标称可工作的拓扑执行多阶段 BO，得到每个拓扑的最优 timing。

4. 完整前仿真  
   对优化后的候选进行：

   - 多灰阶 DATA；
   - D-TFT \(V_{TH}\) variation；
   - mobility variation；
   - 负 \(V_{TH}\)/depletion corner；
   - 温度；
   - ELVDD IR drop；
   - OLED \(V_{TH}\) 和老化；
   - 存储节点 leakage；
   - RC parasitic；
   - Monte Carlo 或 DOE corner。

只有第 4 层结果才能进入最终 Top-10。

为了避免代理模型误删潜在好电路，应保留“性能预测好”和“不确定度高”两类候选，最终排名只能使用真实 SPICE 结果。

## Top-10 的排序方式

不要一开始把所有指标粗暴加权成一个 reward。建议采用：

1. 硬约束淘汰；
2. Pareto front；
3. worst-case robustness；
4. 综合评分；
5. 拓扑多样性去重。

硬约束可以包含：

- 全部工作阶段仿真收敛；
- 补偿与写入确实分离；
- 所有目标灰阶均正常发光；
- 最大 OLED 电流误差低于阈值；
- 编程时间低于 line time；
- 不出现 OLED 瞬时过流；
- 任一关键节点不超过可靠性电压；
- PVT/corner 功能通过率达到要求。

综合指标至少应有：

\[
\begin{aligned}
&\max |\Delta I_\mathrm{OLED}|,\quad
\mathrm{RMS}(\Delta I_\mathrm{OLED}),\\
&t_\mathrm{comp},\quad t_\mathrm{write},\quad
P_\mathrm{avg},\\
&\sum W_iL_i,\quad N_\mathrm{TFT},\quad N_\mathrm{signal},\\
&I_\mathrm{leak},\quad
\mathrm{yield},\quad
\mathrm{worst\text{-}case\ margin}.
\end{aligned}
\]

最终 Top-10 应保留不同连接结构，避免十个结果只是同一个拓扑的轻微尺寸变化。

## 最终判断

最靠谱的技术组合是：

- 拓扑空间定义与完整遍历：自研 Z3/图枚举器；
- 拓扑剪枝与搜索优先级：PixelAI + fast-GateRL；
- 时序搜索：Multi-stage Bayesian Optimization；
- 器件尺寸与 PVT/Pareto：PPAAS；
- 电气正确性：现有 oxide TFT Verilog-A/SmartSpice/HSPICE/Spectre；
- Top-10：真实仿真 Pareto + worst-case 排序。

因此，PixelAI 可以支持你的“功能约束拓扑发现”方向，但不能单独支持完整需求。工程上真正应该建设的是一个“确定性枚举器 + AI 优先搜索 + SPICE 真值验证”的混合系统，而不是纯 RL 系统。这样既能宣称限定空间内不漏拓扑，又能在可接受的算力下完成时序和性能优化。

## 用户 3

你先读相关像素电路领域的论文，基于论文帮我提一些前置的约束，避免节点和时序空间过于大。

## 助手 6 · 进度更新

我会先聚焦与目标最相关的论文类型：氧化物 n 型 D-TFT、内部补偿、写入/补偿分相、低刷新率泄漏与实际时序设计。输出会把约束分成“必须锁死”“建议有限枚举”“暂时不要搜索”三类，并说明每条约束来自哪类像素电路规律。

## 助手 7 · 进度更新

这些论文多数以 PDF 形式发布，我会调用 PDF 阅读工作流来提取电路阶段、节点保存关系和时序边界；它会影响接下来的约束，因为我要以正文和图表描述为准，而不是只依赖摘要。

## 助手 8 · 进度更新

论文里最值得转化为硬约束的一点已经很清楚：补偿值存入后，后续任何直接挂在该存储电容端点上的开关翻转都会带来 kickback；一篇全氧化物 7T2C 工作中，这类结构改动可把相对电流误差推到约 58%。因此“补偿存储节点在写入和发光切换期间受保护”应当成为拓扑生成的一级约束，而不只是仿真后的评分项。

## 助手 9 · 最终答复

基于全氧化物 7T2C、a-IGZO 5T2C、低刷新率 7T1C 等论文，建议第一版搜索空间不要从“任意 TFT 连任意节点”开始，而是限定为：

> n 型 oxide D-TFT + 电压编程 + Reset/Comp/Write/Emit 四阶段 + 5T2C～7T2C + 最多三个模拟状态节点 + 最多四类控制时序。

这能保留主要创新空间，同时把大量明显无效、容易 kickback、无法复位或难以面板实现的组合提前删除。

以下默认 D-TFT 为 n 型 oxide。SWT 器件类型不要在同一次搜索中自由分配；“全 oxide”和“oxide D-TFT + 固定类型 SWT”应分成两个独立任务。

## 一、必须锁死的拓扑约束

### 1. 固定基本电流路径

第一版只允许：

\[
V_{\mathrm{DD}}
\rightarrow D\text{-TFT}
\rightarrow \text{可选 EM 开关}
\rightarrow OLED
\rightarrow GND
\]

约束：

- 恰好一个 D-TFT；
- D-TFT 必须是唯一决定发光电流的晶体管；
- 不搜索 D-TFT 并联、串联双驱动管；
- OLED 极性和电源方向固定；
- OLED 发光路径中最多允许两个额外串联开关。

这是 n 型 a-IGZO 像素电路最常见的基本结构。全氧化物像素通常仍需要四个以上 TFT 完成内部补偿。[Oxide TFTs for AMOLED TVs](https://sid.onlinelibrary.wiley.com/doi/full/10.1002/j.2637-496X.2013.tb00593.x)

### 2. 固定四阶段状态机

只允许：

\[
\text{Reset}\rightarrow
\text{VTH Compensation}\rightarrow
\text{Data Write}\rightarrow
\text{Emission}
\]

不允许模型自由排列阶段，也不允许第一版生成第五、第六阶段。

这与 2023 年 5T2C 和 2026 年全 a-IGZO 7T2C 的成熟操作方式一致；后者明确把 \(V_{\mathrm{TH}}\) 补偿和数据写入分成独立阶段。[5T2C 论文](https://www.mdpi.com/2072-666X/14/4/857)、[7T2C 论文](https://link.springer.com/article/10.1007/s44469-025-00003-4)

### 3. 固定模拟状态节点数量

定义三个有物理意义的模拟状态节点：

- \(G\)：D-TFT gate；
- \(O\)：D-TFT source/OLED anode 一侧；
- \(X\)：可选的电容耦合或中间存储节点。

约束：

- 除 \(G,O,X\) 外，不允许生成新的浮动模拟节点；
- 控制信号只能连接 TFT gate，不能充当模拟存储节点；
- DATA、VREF、VDD、GND 是外部端口，不作为可重命名节点；
- 任一内部节点必须在至少一个阶段连接到已知电位，或连接到有效存储电容；
- 不允许只连接一个 TFT 端子、没有电容的悬空节点。

这会把原来的任意 \(K^{3N}\) 连接问题压缩为几个有明确角色的节点之间的连接问题。

### 4. 第一轮固定为 2C

主搜索空间建议限定：

\[
5T2C,\ 6T2C,\ 7T2C
\]

原因是“补偿、写入分离”最自然的表达是：

- \(C_{\mathrm{TH}}\)：保存 D-TFT 阈值信息；
- \(C_{\mathrm{DATA}}\)：保存或耦合数据电压。

2026 年 7T2C 就分别用 C1、C2 保存 \(V_{\mathrm{TH}}\) 与 \(V_{\mathrm{DATA}}\)；2023 年 5T2C 也使用两只电容完成阈值/OLED 信息提取和数据阶段的迁移率相关放电。[7T2C](https://link.springer.com/article/10.1007/s44469-025-00003-4)、[5T2C](https://www.mdpi.com/2072-666X/14/4/857)

电容连接约束：

- 每只电容至少有一端连接 \(G,O,X\)；
- 禁止电容连接两个固定电源；
- 禁止两只完全并联的电容；
- 两只电容形成连通、无环的链状结构；
- \(C_{\mathrm{TH}}\) 必须直接或间接参与 \(V_{GS}\) 保存；
- \(C_{\mathrm{DATA}}\) 必须位于 DATA 到 D-TFT 控制电压的传递链上。

4T1C、4T2C、5T1C 可作为第二轮边界扩展，避免第一轮同时混合完全不同的补偿机制。

### 5. DATA 只能有一个入口

约束：

- DATA 只能通过一个写入 TFT 进入像素；
- DATA 不允许同时连接多个状态节点；
- DATA 不允许直接连接 OLED；
- DATA 不允许在补偿阶段与 \(C_{\mathrm{TH}}\) 的敏感端点导通；
- DATA 线电位只在 Write 前后变化，不参与 Reset 和 Comp 的动态搜索。

这可以删除大量没有面板实现价值的多数据入口拓扑。

### 6. VREF 只能有一个

第一版只允许一个 DC 参考端口 VREF：

- VREF 只能参与 Reset、Comp；
- Write 期间可保持连接或断开，但不得改变；
- Emission 期间不得形成 D-TFT gate 的低阻钳位；
- 不搜索两个以上参考电压；
- 不搜索 VREF 的脉冲波形。

2026 年 7T2C 使用固定 VREF，在补偿阶段让 DRT source 收敛到 \(V_{\mathrm{REF}}-V_{\mathrm{TH}}\)。这类终态条件非常适合用于自动判定补偿是否成功。[7T2C 工作阶段](https://link.springer.com/article/10.1007/s44469-025-00003-4)

### 7. SWT gate 只能连接控制线

第一版禁止：

- SWT gate 连接内部模拟节点；
- SWT gate 连接 DATA；
- SWT gate 浮空；
- 自偏置或复杂模拟反馈型 SWT。

允许的模拟反馈只通过 D-TFT 及其源、漏、栅和电容网络完成。

### 8. 源漏等价去重

对于没有明显非对称结构的 SWT：

- 将 source/drain 视为无序端点；
- \(T(A,B,\mathrm{SCAN})\) 与 \(T(B,A,\mathrm{SCAN})\) 视为同一拓扑；
- 相同节点对、相同控制信号的并联 SWT 只保留一个；
- 内部节点重命名后的图同构拓扑只保留一个。

这是减少重复电路数量最有效的图级约束之一。

## 二、最重要的补偿存储保护约束

必须将 \(C_{\mathrm{TH}}\) 端点保护写成硬规则：

> \(V_{\mathrm{TH}}\) 补偿完成以后，任何直接连接 \(C_{\mathrm{TH}}\) 敏感端点的 SWT，都不得在 Write→Emit 期间继续翻转。

允许：

- 先关断补偿路径；
- 通过另一只电容耦合写入 DATA；
- 通过间接节点切换 emission path。

不允许：

- DATA 开关直接挂到 \(C_{\mathrm{TH}}\) 敏感节点并在补偿后翻转；
- EM 开关直接挂到 \(C_{\mathrm{TH}}\) 敏感节点；
- 补偿后反复开关与 \(G\) 或 \(C_{\mathrm{TH}}\) 端点相连的 TFT。

2026 年 7T2C 论文专门比较了这类结构：补偿后直接连接存储电容的开关翻转会导致 kickback，修改后的比较电路相对电流误差最高达到约 58.32%；采用间接连接后，低灰阶误差显著降低。[kickback 对比](https://link.springer.com/article/10.1007/s44469-025-00003-4)

这条规则能同时减少拓扑空间和时序空间。

## 三、各阶段的功能约束

### Reset

必须满足：

- \(C_{\mathrm{TH}}\)、\(C_{\mathrm{DATA}}\) 的前一帧信息可被清除；
- 从两个极端初始状态出发，Reset 结束时得到同一个节点状态；
- D-TFT gate 或其参考端被初始化为 VREF/VDD/GND 中之一；
- OLED anode 被初始化到 GND 或保证 OLED 反偏/零偏；
- 不允许 \(VDD\rightarrow OLED\rightarrow GND\) 的完整导通路径。

2023 年 5T2C 和 2026 年 7T2C 都在初始化阶段显式避免 OLED 发光，以抑制 flicker。[5T2C](https://www.mdpi.com/2072-666X/14/4/857)

### Compensation

必须满足：

- DATA 路径关闭；
- OLED 发光路径断开；
- D-TFT 参与真实的充放电终止过程；
- 至少一只电容的最终电压对 \(V_{\mathrm{TH,DRT}}\) 有明显敏感性；
- 补偿结束条件由 D-TFT 自身截止或达到 \(V_{GS}\approx V_{\mathrm{TH}}\) 产生；
- 不能只把某个预设电压写入电容，却没有经过 D-TFT。

推荐的仿真判定量：

\[
S_{\mathrm{TH}}
=
\frac{\partial V_{\mathrm{MEM,TH}}}
{\partial V_{\mathrm{TH,DRT}}}
\]

有效补偿要求 \(S_{\mathrm{TH}}\) 接近 \(+1\) 或 \(-1\)，具体门槛应由基准电路标定，不必一开始锁死数值。

### Write

必须满足：

- COMP 路径先关断，再打开 DATA；
- DATA 只改变 \(C_{\mathrm{DATA}}\) 或通过电容耦合改变 \(V_{GS}\)；
- \(C_{\mathrm{TH}}\) 中保存的阈值信息不能被覆盖；
- OLED 仍保持不发光；
- 写入结束后的 D-TFT 控制量应对 DATA 单调。

判定量：

\[
G_{\mathrm{DATA}}
=
\frac{\partial V_{GS,\mathrm{emit}}}
{\partial V_{\mathrm{DATA}}}
\]

要求符号正确且非零。

### Emission

必须满足：

- DATA、Reset、Comp 路径全部关闭；
- D-TFT gate 只由存储电容保持；
- OLED 只在该阶段形成完整发光路径；
- D-TFT 在目标灰阶范围内处于预期工作区；
- \(I_{\mathrm{OLED}}\) 对 DATA 单调；
- \(I_{\mathrm{OLED}}\) 对 \(V_{\mathrm{TH,DRT}}\) 的一阶敏感度接近零。

判定量：

\[
S_I=
\frac{\partial \log I_{\mathrm{OLED}}}
{\partial V_{\mathrm{TH,DRT}}}
\]

这比只比较某一个标称电流更适合作为拓扑早筛指标。

## 四、时序空间约束

### 1. 控制信号只允许阶段边界翻转

第一版不允许：

- 阶段内部二次脉冲；
- analog ramp；
- 多电平 clock；
- 任意 edge placement；
- 控制信号在一个阶段内重复开关。

每个控制信号只用一个四位 phase mask 表示：

\[
[R,C,W,E]
\]

建议的允许集合：

| 角色 | Mask |
|---|---|
| Reset only | 1000 |
| Reset + Comp | 1100 |
| Comp only | 0100 |
| Comp + Write 共用路径 | 0110 |
| Write only | 0010 |
| Emit only | 0001 |
| Reset + Emit | 1001 |
| Reset + Comp + Write | 1110 |

暂不允许：

- 1010：Reset、Write 两次不连续导通；
- 0101：Comp、Emit 共用；
- 0011：DATA 路径延续至 Emit；
- 1111：永久导通；
- 任意三次以上翻转模式。

这会把每个控制信号的任意波形搜索变成有限的角色分配。

### 2. 最多四个独立控制波形

全氧化物 7T2C 使用 SCAN1、SCAN2、SCAN3、EM 四类控制波形；5T2C 示例使用四类 scan 控制。因此第一版将上限设为四比较合理。[7T2C timing](https://link.springer.com/article/10.1007/s44469-025-00003-4)、[5T2C timing](https://www.mdpi.com/2072-666X/14/4/857)

进一步约束：

- 相同 phase mask 的 TFT 自动合并到同一控制线；
- 信号名称交换后的时序视为等价；
- 控制线数量作为后续面积/GOA 复杂度目标，而非继续增加搜索维度。

低刷新率 LTPO 研究也明确指出，控制线数量会直接影响 GOA 集成、像素尺寸和 PPI；该工作因此把独立信号线压缩到两类。[低刷新率 7T1C](https://pdfs.semanticscholar.org/be68/4a9c9a9e33dfc88cc328b1514c393ffa4a29.pdf)

### 3. 强制 break-before-make

阶段切换顺序固定为：

- Comp→Write：先断开补偿路径，再打开 DATA；
- Write→Emit：先关闭 DATA，再打开 emission path；
- Emit→Reset：先关闭 emission path，再打开 reset。

只搜索两个非重叠时间：

\[
t_{\mathrm{dead,CW}},\quad t_{\mathrm{dead,WE}}
\]

而不是让所有控制信号边沿相互独立。

### 4. 连续时序只保留 4～6 个变量

建议只优化：

\[
t_R,\ t_C,\ t_W,\ t_E,
t_{\mathrm{dead,CW}},
t_{\mathrm{dead,WE}}
\]

其中：

\[
t_R+t_C+t_W\leq T_H
\]

或满足产品定义的行寻址预算。

不要在分辨率、刷新率和 blanking 尚未确定前锁定微秒数。论文中的示例差异较大：低刷新率 7T1C 使用约 23 μs programming，而不同分辨率和扫描架构的时间预算并不相同。

## 五、第一版不要搜索的内容

这些方向应锁死或放到第二阶段：

- current programming；
- 外部补偿/外部 sensing；
- mobility compensation；
- OLED degradation compensation；
- IR-drop compensation；
- dual-gate oxide TFT；
- P/N complementary TFT；
- SWT 类型自由分配；
- 多个 VREF；
- 多个 DATA 入口；
- 多电平 SCAN/EM；
- n−1、n+1 行信号自由组合；
- 三只以上电容；
- 八只以上 TFT；
- W/L、C 值和拓扑同时优化。

原因不是这些方向不重要，而是它们分别引入新的功能机制。第一轮应只回答：

> 在固定 n 型 oxide D-TFT、写入补偿分离的条件下，哪些拓扑可以可靠消除 D-TFT \(V_{\mathrm{TH}}\) 对发光电流的影响？

拓扑筛选完成后，再对存活电路优化 W/L、C、时序和扩展补偿目标。

## 六、推荐的 V0 搜索语法

```text
Device:
  DRT: exactly 1, n-type oxide
  SWT: 4..6, device family fixed per run
  OLED: exactly 1
  Capacitor: exactly 2

Analog nodes:
  G: DRT gate
  O: DRT source / OLED-side node
  X: optional coupling/storage node
  no additional floating analog nodes

External ports:
  VDD, GND, VREF, VDATA
  control_waveforms <= 4

Phases:
  RESET -> COMP -> WRITE -> EMIT

Hard rules:
  OLED off in RESET/COMP/WRITE
  DATA disconnected in COMP
  compensation path off before DATA path on
  DATA path off before emission path on
  VTH-storage sensitive node protected after COMP
  emission current controlled by stored state
  no VDD-GND short path
  no duplicate parallel SWT
  graph-isomorphic circuits deduplicated
```

## 七、最小早筛仿真集

每个合法拓扑先只跑：

- \(V_{\mathrm{TH}}\)：低、标称、高三点，初始可参考论文常用的 \(-0.5,0,+0.5\) V shift；
- DATA：低灰、中灰、高灰三点；
- 前一帧状态：最低和最高两点。

合计：

\[
3\times3\times2=18
\]

组快速 transient，即可检查：

- Reset 是否消除历史；
- Comp 是否真的采样 \(V_{\mathrm{TH}}\)；
- Write 是否保留补偿量；
- OLED 是否在非发光阶段误亮；
- 发光电流是否对 DATA 单调；
- \(V_{\mathrm{TH}}\) 补偿是否有效。

通过这 18 组功能门之后，才进入连续时序优化和完整 corner 仿真。

这套约束最大的收缩来自四处：固定三类模拟节点、固定四阶段顺序、2C 分工、以及补偿存储节点保护。它们均保留了论文中已经验证有效的像素电路机制，同时删除了大部分无物理意义的节点和边沿排列。

## 用户 4

好，利用这些约束条件，借助上面的一些开源项目，帮我进行初步筛选，你自己设计流程，自己解决过程中的问题，直到输出最终的结果报告

## 助手 10 · 进度更新

我会直接把这件事做成一个可复现的初筛工程，而不是停在方案层：先用 `karpathy-guidelines` 保持搜索器最小、约束显式、结果可验证；完成筛选后用分析报告工作流整理方法、候选 Top-10、证据边界和下一步仿真要求。第一步会先检查本地是否已有 oxide TFT/OLED 模型或相关网表，优先复用现有资产。

## 助手 11 · 进度更新

我会把这次交付定义为“可复现的初筛”，输出实际生成的候选数、淘汰原因、Top 10 拓扑—时序组合及其适用边界。报告面向像素电路研发人员；我先锁定技术报告结构并检查本机可用的仿真模型与仿真器。

## 助手 12 · 进度更新

本机没有现成的 ngspice、a‑IGZO Verilog‑A 模型或像素网表，因此我不会把简化模型包装成“工艺级 SPICE 结论”。我会继续完成初筛，但把仿真层明确降级为行为级瞬态代理；它负责验证功能、节点保持、时序竞争和阈值偏移趋势，最终 Top 10 只作为进入真实 PDK/紧凑模型仿真的候选。开源项目主要复用其“生成—仿真—筛选—Pareto”的工作流，而不是直接套用硅 MOS 参数。

## 助手 13 · 进度更新

约束收缩已经出现了一个很有价值的结果：把“补偿后阈值存储电容两端不允许发光阶段开关直接翻转”设为硬约束后，很多看似不同的 6T2C/7T2C 只是节点重命名，或会退化成失去发光电流路径的无效图。接下来我会保留全部淘汰统计；如果最终只剩少数非同构拓扑，Top 10 将是“拓扑 × 时序”组合，而不会人为凑十个不同原理图。

## 助手 14 · 进度更新

第一轮行为仿真已完成：288 个原始角色拓扑，经硬约束和同构去重后剩 8 个；与 120 组时序交叉后仿真 960 个组合、17,280 个角点，其中 120 个通过功能门槛。当前前十全部落在论文同构的 7T2C 结构上，最佳代理误差约 13.35%，补偿时间集中在 16 µs。这个集中性需要做参数扰动检验，我正在验证它是否只是代理模型参数的偶然结果。

## 助手 15 · 进度更新

鲁棒性审计完成：在开关速度 0.5×/2×、寄生电容 0.5×/2×、C1/C2 ±10% 失配、迁移率 ±20% 的 9 种代理参数场景中，获胜拓扑始终是同一个 7T2C 结构。具体最佳补偿时间会在 8–16 µs 间移动，所以最终报告会把“拓扑结论（稳定）”和“时序排序（模型敏感）”分开表达，并把 8 µs 的高速点纳入稳健 Top 10。现在进入报告封装与审计。

## 助手 16 · 进度更新

报告打包器拒绝了“纯表格报告”，要求至少一个量化图表。这一暂停来自报告技能的交付契约。我现在补用 `data-analytics:visualize-data`：只绘制对决策真正有用的“补偿时间—最坏代理 RCER—地址时间”权衡图，避免把高度接近的综合分数做成误导性的柱状图。

## 助手 17 · 进度更新

我定位到报告打包失败的根因了：不是表格或图表越界，而是打包器自带阅读器的顶栏使用 `100vw`；在 macOS 的经典滚动条模式下，垂直滚动条会让顶栏固定多出 15 px。普通覆盖式滚动条下没有该问题。为了不改写生成的报告运行时，我会用无滚动条的官方无头浏览器模式完成同一套桌面/窄屏验证，并保留阅读器原始内容。

## 助手 18 · 最终答复

初步筛选已完成。核心结论：现有约束下应优先推进受保护双电容 7T2C，暂不投入 6T2C 的 PDK 仿真。

- 生成 288 个角色级拓扑
- 硬约束、同构去重后剩 8 个拓扑
- 交叉 120 组时序，共评估 960 个组合
- 完成 17,280 次行为级瞬态角点运行
- 120 个组合通过功能门槛
- 九种参数扰动下，获胜拓扑始终为 `PX-7A2E8337`

最佳组合是：

- Reset：0.5 µs
- Compensation：16 µs
- Write：0.5 µs
- C→W / W→E dead time：0.05 / 0.05 µs
- 总地址时间：17.1 µs
- 基准代理 RCER：13.35%
- 参数扰动最坏代理 RCER：14.57%

该拓扑与公开的 [Park 等人 a‑IGZO 7T2C 电路](https://link.springer.com/article/10.1007/s44469-025-00003-4)同构。Top 10 实际上是同一稳定拓扑的十组时序，其中保留了两个 8 µs 补偿的高速候选。

交付文件：

- [最终技术报告](./amoled_pixel_screening_report.cacheproof.b7af2d73c3753f1b.html)
- [最终 Top 10 JSON](./results/final_top10.json)
- [全部 960 个组合结果](./results/all_candidates.csv)
- [可复现筛选程序](./screen.py)

需要强调：这是行为级 pre‑SPICE 初筛，不是工艺签核结果。拓扑优先级较稳，但 8–16 µs 的精确补偿时间、绝对 OLED 电流和 RCER 必须用真实 a‑IGZO RPI‑62/Verilog‑A 模型及版图寄生重新确定。报告已通过打包验证、1440/390 px 阅读器验证、测试和缓存哈希校验。

## 用户 5

把我们的对话整理成一份md文档，结合你刚刚输出的交付内容，全部gitpush到我的github账户上。注意保留我们对话的全部内容。设置为public
