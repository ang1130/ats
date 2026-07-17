#!/usr/bin/env python3
"""Build the midterm presentation from the opening-defense template.

The script uses only the Python standard library. It keeps the source deck's
masters, layouts, transitions, media, and existing brand assets intact, then
adds editable PowerPoint text/shape overlays and inserts the verified PoC charts.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(
    "/Users/anshizhao/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
    "xwechat_files/wxid_gskyl58xstkt22_87c9/msg/file/2026-07/安仕钊-开题.pptx"
)
OUTPUT_DIR = ROOT / "deliverables"
OUTPUT = OUTPUT_DIR / "安仕钊-中期进展汇报.pptx"
PDF_OUTPUT = OUTPUT_DIR / "安仕钊-中期进展汇报.pdf"
CHARTS = ROOT / "ats-sim" / "results" / "figures"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}
for prefix, uri in NS.items():
    if prefix not in {"rel", "ct"}:
        ET.register_namespace(prefix, uri)

A = "{%s}" % NS["a"]
P = "{%s}" % NS["p"]
R = "{%s}" % NS["r"]
REL = "{%s}" % NS["rel"]
CT = "{%s}" % NS["ct"]

DARK = "3E3D4F"
BLUE = "0070C0"
MID_BLUE = "42719B"
LIGHT_BLUE = "EAF3FB"
PALE = "F5F7FA"
TEXT = "2B2B35"
GRAY = "6F7280"
RED = "C00000"
WHITE = "FFFFFF"


def qname(prefix: str, tag: str) -> str:
    return {"a": A, "p": P, "r": R, "rel": REL, "ct": CT}[prefix] + tag


def xml(path: Path) -> ET.ElementTree:
    return ET.parse(path)


def text_of(shape: ET.Element) -> str:
    return "".join(node.text or "" for node in shape.findall(".//a:t", NS))


def set_shape_text(shape: ET.Element, text: str) -> bool:
    nodes = shape.findall(".//a:t", NS)
    if not nodes:
        return False
    nodes[0].text = text
    for node in nodes[1:]:
        node.text = ""
    return True


def replace_text(slide: ET.Element, old: str, new: str) -> bool:
    for shape in slide.findall(".//p:sp", NS):
        if old in text_of(shape):
            return set_shape_text(shape, new)
    return False


def sp_tree(slide: ET.Element) -> ET.Element:
    tree = slide.find("p:cSld/p:spTree", NS)
    if tree is None:
        raise RuntimeError("slide shape tree missing")
    return tree


def next_shape_id(slide: ET.Element) -> int:
    ids = []
    for node in slide.findall(".//p:cNvPr", NS):
        try:
            ids.append(int(node.get("id", "0")))
        except ValueError:
            pass
    return max(ids, default=0) + 1


def color(parent: ET.Element, value: str) -> None:
    ET.SubElement(parent, qname("a", "srgbClr"), {"val": value})


def add_shape(
    slide: ET.Element,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = WHITE,
    line: str | None = None,
    radius: bool = False,
) -> ET.Element:
    shape_id = next_shape_id(slide)
    shape = ET.Element(qname("p", "sp"))
    nv = ET.SubElement(shape, qname("p", "nvSpPr"))
    ET.SubElement(nv, qname("p", "cNvPr"), {"id": str(shape_id), "name": name})
    ET.SubElement(nv, qname("p", "cNvSpPr"))
    ET.SubElement(nv, qname("p", "nvPr"))
    sppr = ET.SubElement(shape, qname("p", "spPr"))
    xfrm = ET.SubElement(sppr, qname("a", "xfrm"))
    ET.SubElement(xfrm, qname("a", "off"), {"x": str(int(x * 12700)), "y": str(int(y * 12700))})
    ET.SubElement(xfrm, qname("a", "ext"), {"cx": str(int(w * 12700)), "cy": str(int(h * 12700))})
    geom = ET.SubElement(sppr, qname("a", "prstGeom"), {"prst": "roundRect" if radius else "rect"})
    ET.SubElement(geom, qname("a", "avLst"))
    solid = ET.SubElement(sppr, qname("a", "solidFill"))
    color(solid, fill)
    if line is None:
        ln = ET.SubElement(sppr, qname("a", "ln"))
        ET.SubElement(ln, qname("a", "noFill"))
    else:
        ln = ET.SubElement(sppr, qname("a", "ln"), {"w": "9525"})
        solid_ln = ET.SubElement(ln, qname("a", "solidFill"))
        color(solid_ln, line)
    sp_tree(slide).append(shape)
    return shape


def add_text(
    slide: ET.Element,
    name: str,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size: float = 16,
    color_value: str = TEXT,
    bold: bool = False,
    align: str = "l",
    font: str = "Microsoft YaHei",
) -> ET.Element:
    shape = add_shape(slide, name, x, y, w, h, fill=WHITE, line=None)
    shape.find("p:nvSpPr/p:cNvSpPr", NS).set("txBox", "1")
    tx_body = ET.SubElement(shape, qname("p", "txBody"))
    ET.SubElement(tx_body, qname("a", "bodyPr"), {"wrap": "square", "rtlCol": "0"})
    ET.SubElement(tx_body, qname("a", "lstStyle"))
    for line in text.split("\n"):
        paragraph = ET.SubElement(tx_body, qname("a", "p"))
        ppr = ET.SubElement(paragraph, qname("a", "pPr"), {"algn": align})
        run = ET.SubElement(paragraph, qname("a", "r"))
        rpr_attrs = {"lang": "zh-CN", "sz": str(int(size * 100))}
        if bold:
            rpr_attrs["b"] = "1"
        rpr = ET.SubElement(run, qname("a", "rPr"), rpr_attrs)
        latin = ET.SubElement(rpr, qname("a", "latin"), {"typeface": font})
        ET.SubElement(rpr, qname("a", "ea"), {"typeface": font})
        fill = ET.SubElement(rpr, qname("a", "solidFill"))
        color(fill, color_value)
        ET.SubElement(run, qname("a", "t")).text = line
        end = ET.SubElement(paragraph, qname("a", "endParaRPr"), {"lang": "zh-CN", "sz": str(int(size * 100))})
        ET.SubElement(end, qname("a", "latin"), {"typeface": font})
        ET.SubElement(end, qname("a", "ea"), {"typeface": font})
        end_fill = ET.SubElement(end, qname("a", "solidFill"))
        color(end_fill, color_value)
    return shape


def add_card(slide: ET.Element, title: str, body: str, x: float, y: float, w: float, h: float, accent: str = BLUE) -> None:
    add_shape(slide, f"card-{title}", x, y, w, h, fill=WHITE, line="D9E2F0", radius=True)
    add_shape(slide, f"accent-{title}", x, y, 5, h, fill=accent, line=None, radius=True)
    add_text(slide, f"title-{title}", title, x + 14, y + 10, w - 25, 18, 14, accent, True)
    add_text(slide, f"body-{title}", body, x + 14, y + 31, w - 25, h - 38, 10.5, TEXT)


def add_footer_note(slide: ET.Element) -> None:
    add_text(
        slide,
        "preliminary-boundary",
        "注：当前结果为单跳 Python/SimPy proof-of-concept 初步输出，仅用于趋势分析，不作为最终论文定量结论。",
        40,
        355,
        610,
        12,
        7.6,
        GRAY,
    )


def make_png(svg: Path, output: Path, width: int = 1800) -> None:
    subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(output), str(svg)], check=True)


def add_image(slide: ET.Element, rels: ET.ElementTree, media_name: str, x: float, y: float, w: float, h: float) -> None:
    rel_root = rels.getroot()
    existing = [int(rel.get("Id", "rId0")[3:]) for rel in rel_root.findall("rel:Relationship", NS) if rel.get("Id", "").startswith("rId") and rel.get("Id", "")[3:].isdigit()]
    rid = f"rId{max(existing, default=0) + 1}"
    ET.SubElement(
        rel_root,
        qname("rel", "Relationship"),
        {
            "Id": rid,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
            "Target": f"../media/{media_name}",
        },
    )
    shape_id = next_shape_id(slide)
    pic = ET.Element(qname("p", "pic"))
    nv = ET.SubElement(pic, qname("p", "nvPicPr"))
    ET.SubElement(nv, qname("p", "cNvPr"), {"id": str(shape_id), "name": media_name})
    c_nv_pic = ET.SubElement(nv, qname("p", "cNvPicPr"))
    ET.SubElement(c_nv_pic, qname("a", "picLocks"), {"noChangeAspect": "1"})
    ET.SubElement(nv, qname("p", "nvPr"))
    blip_fill = ET.SubElement(pic, qname("p", "blipFill"))
    ET.SubElement(blip_fill, qname("a", "blip"), {R + "embed": rid})
    stretch = ET.SubElement(blip_fill, qname("a", "stretch"))
    ET.SubElement(stretch, qname("a", "fillRect"))
    sppr = ET.SubElement(pic, qname("p", "spPr"))
    xfrm = ET.SubElement(sppr, qname("a", "xfrm"))
    ET.SubElement(xfrm, qname("a", "off"), {"x": str(int(x * 12700)), "y": str(int(y * 12700))})
    ET.SubElement(xfrm, qname("a", "ext"), {"cx": str(int(w * 12700)), "cy": str(int(h * 12700))})
    geom = ET.SubElement(sppr, qname("a", "prstGeom"), {"prst": "rect"})
    ET.SubElement(geom, qname("a", "avLst"))
    sp_tree(slide).append(pic)


def cover_body(slide: ET.Element) -> None:
    # Covers opening-defense content while preserving the header/logo and footer/page number.
    add_shape(slide, "midterm-content-canvas", 18, 57, 670, 290, fill=WHITE, line=None)


def set_chapter(slide: ET.Element, number: str, title: str) -> None:
    replace_text(slide, "第一部分", number)
    replace_text(slide, "第二部分", number)
    replace_text(slide, "第三部分", number)
    replace_text(slide, "第四部分", number)
    replace_text(slide, "第五部分", number)
    for shape in slide.findall(".//p:sp", NS):
        value = text_of(shape)
        if value in {"研究背景与问题", "国内外研究现状", "核心思想和步骤", "预期成果", "研究意义与应用价值"}:
            set_shape_text(shape, title)


def build_slide_4(slide: ET.Element) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "ATS 参数静态配置在动态场景下面临失配", 42, 68, 590, 26, 22, DARK, True)
    add_card(slide, "动态工业流量", "周期控制流、事件告警流与 BE 背景流共存；设备上线、任务切换和突发告警会形成负载高峰。", 42, 108, 198, 112)
    add_card(slide, "固定参数失配", "固定 CIR/CBS 在高峰时可能导致排队、丢包和 deadline 违约；在低谷时又可能造成资源过度预留。", 261, 108, 198, 112, MID_BLUE)
    add_card(slide, "研究问题", "如何基于网络状态反馈，轻量、可解释地在线调整 CIR/CBS，并兼顾关键流性能与资源占用？", 480, 108, 198, 112, "008C95")
    add_text(slide, "ats-note", "ATS 面向异步、突发流量；本研究关注动态 IIoT 中静态整形参数难以持续适配的问题。", 54, 248, 600, 28, 13, BLUE, True, "c")


def build_slide_6(slide: ET.Element) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "开题目标与当前阶段进展", 42, 68, 590, 26, 22, DARK, True)
    rows = [
        ("参数建模", "(r,b) → (CIR,CBS,MRT)", "已完成"),
        ("动态场景", "低负载—高峰—ET burst—回落", "已完成"),
        ("规则库", "R1–R6、cooldown、防抖、R4 迟滞", "已完成初版"),
        ("对比实验", "四组 baseline + CIR/CBS 离散网格", "已完成 PoC"),
        ("规则预标定", "四个参数变体的小型探索性筛选", "已完成"),
        ("高保真验证", "OMNeT++/INET ATS 迁移与正式实验", "后续工作"),
    ]
    x0, widths = 42, (105, 382, 112)
    y = 108
    for label, width in zip(("开题目标", "当前阶段产出", "状态"), widths):
        add_shape(slide, f"table-header-{label}", x0, y, width, 24, fill=DARK, line=WHITE)
        add_text(slide, f"table-header-text-{label}", label, x0 + 5, y + 5, width - 10, 14, 10.5, WHITE, True, "c")
        x0 += width
    y += 24
    for index, (goal, progress, status) in enumerate(rows):
        x0 = 42
        fill = WHITE if index % 2 == 0 else PALE
        for value, width, label in zip((goal, progress, status), widths, ("goal", "progress", "status")):
            add_shape(slide, f"table-{label}-{index}", x0, y, width, 31, fill=fill, line="D9E2F0")
            status_color = "008C95" if status != "后续工作" else BLUE
            add_text(slide, f"table-text-{label}-{index}", value, x0 + 5, y + 7, width - 10, 18, 9.3, status_color if label == "status" else TEXT, label == "status", "c" if label != "progress" else "l")
            x0 += width
        y += 31


def build_slide_7(slide: ET.Element) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "文献阅读后的模型修正与 Python PoC 边界", 42, 68, 620, 26, 21, DARK, True)
    add_card(slide, "开题初始描述", "x = (r, b)\n以令牌桶速率与突发容量描述整形参数。", 52, 112, 178, 90, MID_BLUE)
    add_text(slide, "arrow-model", "→", 241, 134, 36, 30, 30, BLUE, True, "c")
    add_card(slide, "文献修正后", "x = (CIR, CBS, MRT)\n采用 ATS 文献中的参数语言。", 282, 112, 178, 90, BLUE)
    add_text(slide, "arrow-stage", "→", 471, 134, 36, 30, 30, BLUE, True, "c")
    add_card(slide, "当前执行范围", "x_stage1 = (CIR, CBS)\nMRT 仅保留为理论/配置占位量。", 512, 112, 158, 90, "008C95")
    add_text(slide, "boundary", "Python/SimPy：单跳 CIR/CBS 令牌桶近似，用于规则逻辑与参数范围预筛选。\n当前不执行 MRT residence-time/MRT drop 语义；最终结果以 OMNeT++/INET 高保真验证为准。", 58, 235, 600, 47, 12, TEXT, False, "c")


def build_slide_9(slide: ET.Element) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "基于状态反馈的 ATS 参数自适应框架", 42, 68, 590, 26, 22, DARK, True)
    boxes = [
        ("动态流量", "TT/ET + BE\n负载变化 / burst", 42, 130, MID_BLUE),
        ("ATS Shaper", "CIR/CBS\n单跳近似", 174, 130, BLUE),
        ("Monitor", "q, λ, d_obs\nσ, token, drop", 306, 130, "008C95"),
        ("Rule Engine", "R1–R6\n状态反馈决策", 438, 130, BLUE),
        ("参数动作", "调整 CIR/CBS\n记录规则日志", 570, 130, MID_BLUE),
    ]
    for index, (title, body, x, y, accent) in enumerate(boxes):
        add_card(slide, f"framework-{index}", f"{title}\n{body}", x, y, 108, 83, accent)
        if index < len(boxes) - 1:
            add_text(slide, f"framework-arrow-{index}", "→", x + 108, y + 29, 24, 20, 20, BLUE, True, "c")
    add_text(slide, "framework-outcome", "输出：关键流时延、deadline violation、drop、吞吐与 CIR/CBS 参数轨迹", 72, 250, 575, 22, 14, DARK, True, "c")


def build_slide_10(slide: ET.Element, rels: ET.ElementTree, media: dict[str, str]) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "R1–R6 规则库与 R4 迟滞修正", 42, 68, 590, 26, 22, DARK, True)
    rules = [
        ("R1", "队列增长\n+ 到达率上升", "增 CIR"),
        ("R2", "时延接近\ndeadline", "增 CIR/CBS"),
        ("R3", "突发强度\n升高", "增 CBS"),
        ("R4", "连续低负载", "降 CIR"),
        ("R5", "发生丢包", "紧急扩容"),
        ("R6", "稳态运行", "回归默认"),
    ]
    for i, (rule, trigger, action) in enumerate(rules):
        row, col = divmod(i, 3)
        x, y = 45 + col * 211, 108 + row * 74
        add_shape(slide, f"rule-card-{rule}", x, y, 193, 60, fill=LIGHT_BLUE, line="C9D9EC", radius=True)
        add_text(slide, f"rule-number-{rule}", rule, x + 9, y + 9, 28, 18, 12, BLUE, True, "c")
        add_text(slide, f"rule-trigger-{rule}", trigger, x + 41, y + 8, 91, 36, 9.4, TEXT, True)
        add_text(slide, f"rule-action-{rule}", action, x + 135, y + 20, 50, 16, 9.4, "008C95", True, "c")
    add_shape(slide, "r4-highlight", 45, 267, 630, 41, fill="FFF4E5", line="F4B183", radius=True)
    add_text(slide, "r4-title", "R4 迟滞修正：", 57, 278, 100, 16, 10.5, RED, True)
    add_text(slide, "r4-detail", "扩容后保持时间 + 连续低负载窗口 + 更小降速步长，使 R4 触发次数由 23 次降至 5 次。", 157, 278, 490, 16, 10.5, TEXT)
    add_footer_note(slide)


def build_slide_12(slide: ET.Element, rels: ET.ElementTree, media: dict[str, str]) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "Preliminary 实验设计与四组方法对比", 42, 68, 620, 26, 22, DARK, True)
    add_text(slide, "experiment-tags", "动态场景：低负载 → 高峰流量增加 → ET burst → 负载回落     主展示：relaxed 10 ms profile     seed = 42", 42, 98, 630, 14, 8.8, GRAY, False, "c")
    add_image(slide, rels, media["metrics"], 38, 120, 400, 226)
    add_text(slide, "comparison-title", "relaxed profile 核心观察", 461, 123, 205, 18, 12, BLUE, True)
    table = [
        ("Static-Low", "39.53%", "98.78%"),
        ("Static-High", "0.30%", "60.30%"),
        ("Offline candidate", "0.00%", "0.00%"),
        ("Rule-Based", "0.00%", "42.11%"),
    ]
    y = 149
    for i, (method, drop, violation) in enumerate(table):
        fill = PALE if i % 2 else WHITE
        add_shape(slide, f"method-row-{i}", 456, y, 216, 25, fill=fill, line="D9E2F0")
        add_text(slide, f"method-{i}", method, 461, y + 6, 93, 13, 7.8, TEXT, i == 3)
        add_text(slide, f"drop-{i}", f"drop {drop}", 554, y + 6, 58, 13, 7.6, RED if i == 0 else TEXT, False, "c")
        add_text(slide, f"viol-{i}", f"违约 {violation}", 612, y + 6, 55, 13, 7.6, RED if i in (0, 1) else "008C95", False, "c")
        y += 25
    add_text(slide, "result-summary", "• Static-Low 在动态场景下明显失配。\n• Rule-Based 相对 Static-Low 呈改善趋势。\n• 当前 CIR/CBS 网格的离线候选仍更优，规则库尚需标定。", 464, 264, 205, 57, 9.2, TEXT)
    add_footer_note(slide)


def build_slide_14(slide: ET.Element, rels: ET.ElementTree, media: dict[str, str]) -> None:
    cover_body(slide)
    add_text(slide, "slide-title", "动态过程、预标定方向与 OMNeT++/INET 迁移路线", 38, 68, 640, 24, 19, DARK, True)
    add_image(slide, rels, media["delay"], 38, 98, 300, 128)
    add_image(slide, rels, media["trajectory"], 38, 230, 300, 116)
    add_text(slide, "calibration-title", "小型预标定（relaxed）", 364, 100, 270, 16, 11.5, BLUE, True)
    variants = [
        ("Current-Rule", "56.841 ms", "42.11%"),
        ("Aggressive-CIR", "19.819 ms", "7.52%"),
        ("CIR-Focused-Low-CBS", "12.346 ms", "3.01%"),
        ("Conservative-Return", "11.653 ms", "3.27%"),
    ]
    y = 122
    for i, (variant, p99, violation) in enumerate(variants):
        add_shape(slide, f"variant-row-{i}", 360, y, 308, 25, fill=PALE if i % 2 else WHITE, line="D9E2F0")
        add_text(slide, f"variant-name-{i}", variant, 365, y + 6, 142, 13, 7.8, TEXT, i in (2, 3))
        add_text(slide, f"variant-p99-{i}", p99, 510, y + 6, 70, 13, 7.8, TEXT, False, "c")
        add_text(slide, f"variant-viol-{i}", violation, 585, y + 6, 76, 13, 7.8, "008C95" if i in (2, 3) else RED, False, "c")
        y += 25
    add_text(slide, "calibration-summary", "方向：更偏向 CIR 提升、减少 CBS 的非必要增长、减慢回退，可改善当前 PoC 表现；仍需高保真复验。", 365, 235, 295, 33, 9.2, TEXT)
    add_text(slide, "migration-title", "中期后迁移路线", 364, 282, 245, 16, 11.5, BLUE, True)
    add_text(slide, "migration", "ATS showcase / 模块核验  →  最小 TSN 拓扑  →  静态 baseline\n→  Rule-Based controller  →  多 seed、多场景与参数敏感性", 365, 302, 295, 34, 9.2, DARK, True, "c")
    add_footer_note(slide)


def update_cover(slide: ET.Element) -> None:
    replace_text(slide, "毕业论文开题答辩", "毕业论文中期进展汇报")
    replace_text(slide, "2025年11月20日", "2026年7月17日")


def update_agenda(slide: ET.Element) -> None:
    # The opening deck uses grouped, decorative agenda items. Overlay a clean editable agenda while retaining header/footer branding.
    add_shape(slide, "agenda-canvas", 26, 80, 650, 250, fill=WHITE, line=None)
    add_text(slide, "agenda-title", "目录", 47, 90, 90, 24, 23, DARK, True)
    items = [
        "01  研究背景与问题",
        "02  开题目标与当前进展",
        "03  方法与规则库设计",
        "04  Preliminary 实验结果",
        "05  阶段结论与后续计划",
    ]
    for index, item in enumerate(items):
        y = 130 + index * 35
        add_shape(slide, f"agenda-number-{index}", 65, y, 46, 25, fill=BLUE, line=None, radius=True)
        add_text(slide, f"agenda-number-text-{index}", f"{index + 1:02d}", 65, y + 5, 46, 13, 10, WHITE, True, "c")
        add_text(slide, f"agenda-item-{index}", item[4:], 130, y + 4, 330, 16, 15, TEXT, index == 3)


def update_thanks(slide: ET.Element) -> None:
    replace_text(slide, "谢谢", "谢谢")
    replace_text(slide, "请各位老师批评指正！", "请各位老师批评指正！")
    add_text(slide, "thanks-subtitle", "中期阶段性汇报", 250, 300, 220, 18, 12, WHITE, False, "c")


def copy_and_unpack() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    if OUTPUT.exists():
        OUTPUT.unlink()
    shutil.copy2(TEMPLATE, OUTPUT)
    OUTPUT.chmod(0o644)
    temp = Path(tempfile.mkdtemp(prefix="ats-midterm-ppt-"))
    with zipfile.ZipFile(OUTPUT) as archive:
        archive.extractall(temp)
    return temp


def write_back(workdir: Path) -> None:
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workdir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(workdir).as_posix())


def add_png_content_type(workdir: Path) -> None:
    content_types = workdir / "[Content_Types].xml"
    tree = xml(content_types)
    root = tree.getroot()
    if not any(item.get("Extension") == "png" for item in root.findall("ct:Default", NS)):
        ET.SubElement(root, qname("ct", "Default"), {"Extension": "png", "ContentType": "image/png"})
    tree.write(content_types, encoding="UTF-8", xml_declaration=True)


def main() -> None:
    workdir = copy_and_unpack()
    add_png_content_type(workdir)
    media_dir = workdir / "ppt" / "media"
    media_dir.mkdir(exist_ok=True)
    chart_sources = {
        "metrics": CHARTS / "metrics_bar_relaxed.svg",
        "delay": CHARTS / "delay_timeseries_relaxed.svg",
        "trajectory": CHARTS / "cir_cbs_trajectory_relaxed.svg",
        "timeline": CHARTS / "rule_timeline_relaxed.svg",
    }
    media: dict[str, str] = {}
    for key, source in chart_sources.items():
        target_name = f"midterm_{key}.png"
        make_png(source, media_dir / target_name)
        media[key] = target_name

    slides = {}
    rels = {}
    for number in range(1, 16):
        slides[number] = xml(workdir / "ppt" / "slides" / f"slide{number}.xml")
        rels[number] = xml(workdir / "ppt" / "slides" / "_rels" / f"slide{number}.xml.rels")

    update_cover(slides[1].getroot())
    update_agenda(slides[2].getroot())
    set_chapter(slides[3].getroot(), "第一部分", "研究背景与问题")
    build_slide_4(slides[4].getroot())
    set_chapter(slides[5].getroot(), "第二部分", "开题目标与当前进展")
    build_slide_6(slides[6].getroot())
    build_slide_7(slides[7].getroot())
    set_chapter(slides[8].getroot(), "第三部分", "方法与规则库设计")
    build_slide_9(slides[9].getroot())
    build_slide_10(slides[10].getroot(), rels[10], media)
    set_chapter(slides[11].getroot(), "第四部分", "Preliminary 实验结果")
    build_slide_12(slides[12].getroot(), rels[12], media)
    set_chapter(slides[13].getroot(), "第五部分", "阶段结论与后续计划")
    build_slide_14(slides[14].getroot(), rels[14], media)
    update_thanks(slides[15].getroot())

    for number in range(1, 16):
        slide_path = workdir / "ppt" / "slides" / f"slide{number}.xml"
        rel_path = workdir / "ppt" / "slides" / "_rels" / f"slide{number}.xml.rels"
        slides[number].write(slide_path, encoding="UTF-8", xml_declaration=True)
        rels[number].write(rel_path, encoding="UTF-8", xml_declaration=True)

    write_back(workdir)
    shutil.rmtree(workdir)
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()
