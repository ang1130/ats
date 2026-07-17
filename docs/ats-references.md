# 仿真参数文献依据

> 用于支撑 M4 流量参数、M2 链路参数的取值，使合成流量"可信"。
> 边查边补，标注出处。

## 1. 链路带宽
- **1 Gbps**：TSN 仿真最典型链路速率（CyclicSim/INET 框架默认）。
- 出处：Debnath et al., "CyclicSim", arXiv:2409.19792 (2024)；多数 TSN 仿真文献默认值。

## 2. TT（周期控制流）
- **周期 T_c**：1, 2, 5, 10, 50 ms 常用
- **包长 L_c**：64–1500 字节（常用 64, 128, 256, 512, 1500 B）
- 出处：Craciunas et al., "Scheduling Real-Time Communication in IEEE 802.1Qbv TSN", EMSOFT 2016 —— TT 周期 1–10ms，帧长至 1500B。
- **本研究取值**：T_c ∈ {2, 5, 10} ms，L_c ∈ {64, 128} B（小控制包）。

## 3. ET（事件触发流）
- 泊松/突发到达，包长 64–512 B。
- 出处：Zhao et al., "Performance Comparison of IEEE 802.1 TSN Features"。
- **本研究取值**：突发注入，包长 128 B。

## 4. BE（尽力而为流）
- CBR 或泊松，包长 64–1500 B，常用于占满剩余带宽。
- **本研究取值**：泊松到达，包长 1500 B（大背景包）。

## 5. 时延红线
- **D_max = 10 ms**：工业闭环控制典型量级。
- 出处：IEC/IEEE 60802 TSN profile for industrial automation；运动控制 ~1ms，一般闭环控制 ~10ms。

## 6. 直接相关方法论文（对照/参考）
- Yu et al., "Efficient Adaptive Bandwidth Allocation for Deadline-Aware Online Admission Control in TSN", arXiv:2503.09093 (2025) —— ATS+CBS 在线自适应，**最近对照**。
- Debnath et al., "CyclicSim", arXiv:2409.19792 (2024) —— OMNeT++ TSN 框架，中期后迁移基础。
- Maile et al., "On the Effect of TSN Forwarding Mechanisms on Best-Effort Traffic", arXiv:2408.01330 (2024) —— ATS 对 BE 流影响参考。
- Craciunas et al., EMSOFT 2016 —— TT 流量参数经典出处。

## 已用于当前文献参数映射的直接基线

- **Yoshimura, A.; Ito, Y.** *A Study on Optimal Ethernet-based Industrial Networks Construction Using Asynchronous Traffic Shaping in IEEE 802.1TSN and Downhill Simplex Method.* ICOIN 2025. DOI: `10.1109/ICOIN63865.2025.10992702`。
  - 当前项目已从该文献整理了流量参数和 Offline 静态优化的研究参照；Python PoC 采用的是 CIR/CBS 离散网格近似，而非原文的完整 Downhill Simplex 复现。

## 待补/待进一步核验

- Wu et al. 2025（队列理论令牌桶自适应）—— 规则库启发源。
- Lübeck et al. 2025（ATS 非 FIFO 无界延迟）—— 机制改进参考。
- 李琳 et al. 2025 HTS（混合整形）—— 相关工作。
