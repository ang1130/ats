# 中期答辩 PPT 交付说明

## 文件

- `安仕钊-中期进展汇报.pptx`：可编辑的 15 页中期答辩演示文稿。

该文件以用户提供的 `安仕钊-开题.pptx` 为底稿生成，保留原有 16:9 规格、学校品牌资产、封面/目录/五个章节页/正文/致谢结构及原章节页转场资源。

## 内容来源

- `docs/midterm-ppt-outline.md`
- `docs/midterm-presentation-script.md`
- `docs/midterm-preliminary-results-page.md`
- `docs/midterm-progress-comparison.md`
- `ats-sim/results/figures/*_relaxed.svg`

## 结果边界

第 10、12、14 页均带有统一注记：

> 注：当前结果为单跳 Python/SimPy proof-of-concept 初步输出，仅用于趋势分析，不作为最终论文定量结论。

主结果页使用 relaxed profile；strict profile 不作为主图展示。当前 Python PoC 仅在线调整 CIR/CBS，MRT 仅保留为理论/配置占位量，未在执行模型中实施 residence-time/MRT drop 语义。

## 建议的最终人工检查

请用 Microsoft PowerPoint 打开并在全屏模式下检查一次：

1. 当前系统的中文字体是否发生替换；
2. 第 12、14 页图表在投影分辨率下的可读性；
3. 封面日期、姓名、专业和导师信息是否需要更新；
4. 是否需要根据实际答辩时长删减第 14 页内容。

由于 PowerPoint AppleScript 的 PDF 导出没有在本机稳定生成输出，本次仅交付并验证 `.pptx`；如需 PDF，请在 PowerPoint 中使用“导出 / 创建 PDF”完成导出。
