"""Generate Excalidraw JSON files for CHITCHAT architecture diagrams.

Produces two .excalidraw files with PROPER text bindings so labels render in
excalidraw.com (the MCP `label` shorthand does not survive export).

Run:
    python docs/diagrams/generate.py
"""

import json
import random
from pathlib import Path

OUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Element builders
# ---------------------------------------------------------------------------

_seed_counter = [1]


def _seed():
    _seed_counter[0] += 1
    return _seed_counter[0]


def _base(eid, etype, x, y, w, h, *, stroke="#1e1e1e", fill="transparent",
          fill_style="solid", stroke_width=2, opacity=100, roundness=True,
          stroke_style="solid"):
    el = {
        "type": etype,
        "id": eid,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": fill_style,
        "strokeWidth": stroke_width,
        "strokeStyle": stroke_style,
        "roughness": 1,
        "opacity": opacity,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3} if roundness and etype != "arrow" else None,
        "seed": _seed(),
        "version": 1,
        "versionNonce": random.randint(1, 2**31),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }
    return el


def text(eid, x, y, w, h, content, font_size=18, color="#1e1e1e",
         container_id=None, align="center"):
    t = _base(eid, "text", x, y, w, h, stroke=color, roundness=False)
    t["fontSize"] = font_size
    t["fontFamily"] = 1  # Virgil
    t["text"] = content
    t["textAlign"] = align
    t["verticalAlign"] = "middle" if container_id else "top"
    t["containerId"] = container_id
    t["originalText"] = content
    t["lineHeight"] = 1.25
    t["baseline"] = int(font_size * 0.85)
    return t


def labeled_box(eid, x, y, w, h, label, *, fill, stroke, font_size=18,
                text_color="#1e1e1e", font_color=None):
    """Returns [rect, text] with proper container binding."""
    rect = _base(eid, "rectangle", x, y, w, h, stroke=stroke, fill=fill)
    tid = f"{eid}_t"
    rect["boundElements"] = [{"id": tid, "type": "text"}]
    txt = text(tid, x, y, w, h, label, font_size=font_size,
               color=font_color or text_color, container_id=eid)
    return [rect, txt]


def zone(eid, x, y, w, h, *, fill, stroke):
    return _base(eid, "rectangle", x, y, w, h, stroke=stroke, fill=fill,
                 stroke_width=1, opacity=30)


def arrow(eid, x, y, dx, dy, *, stroke="#1e1e1e", stroke_width=2,
          dashed=False, start_binding=None, end_binding=None):
    a = _base(eid, "arrow", x, y, abs(dx) if dx else 0, abs(dy) if dy else 0,
              stroke=stroke, stroke_width=stroke_width, roundness=False,
              stroke_style="dashed" if dashed else "solid")
    a["points"] = [[0, 0], [dx, dy]]
    a["lastCommittedPoint"] = None
    a["startBinding"] = start_binding
    a["endBinding"] = end_binding
    a["startArrowhead"] = None
    a["endArrowhead"] = "arrow"
    a["elbowed"] = False
    return a


def arrow_with_label(eid, x, y, dx, dy, label_text, *, font_size=14,
                     stroke="#1e1e1e", stroke_width=2):
    """Arrow + bound midpoint text label."""
    a = arrow(eid, x, y, dx, dy, stroke=stroke, stroke_width=stroke_width)
    tid = f"{eid}_lbl"
    a["boundElements"] = [{"id": tid, "type": "text"}]
    # Position text at midpoint
    mx = x + dx / 2
    my = y + dy / 2
    est_w = max(80, len(label_text) * font_size * 0.55)
    t = text(tid, mx - est_w / 2, my - font_size,
             est_w, font_size + 4, label_text,
             font_size=font_size, container_id=eid)
    return [a, t]


def wrap_file(elements):
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": None,
        },
        "files": {},
    }


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

C = {
    "data_fill": "#fff3bf",
    "data_stroke": "#a16207",
    "script_fill": "#d0bfff",
    "script_stroke": "#6d28d9",
    "external_fill": "#ffd8a8",
    "external_stroke": "#c2410c",
    "input_fill": "#a5d8ff",
    "input_stroke": "#1d4ed8",
    "output_fill": "#b2f2bb",
    "output_stroke": "#15803d",
    "decision_fill": "#fff3bf",
    "decision_stroke": "#a16207",
    "result_fill": "#eebefa",
    "result_stroke": "#a21caf",
    "zone1_fill": "#dbe4ff",
    "zone1_stroke": "#2563eb",
    "zone2_fill": "#e5dbff",
    "zone2_stroke": "#7c3aed",
    "zone3_fill": "#d3f9d8",
    "zone3_stroke": "#16a34a",
    "zone4_fill": "#ffe8cc",
    "zone4_stroke": "#ea580c",
}


# ---------------------------------------------------------------------------
# Diagram 1: Pipeline Architecture
# ---------------------------------------------------------------------------

def build_pipeline():
    els = []

    # Title
    els.append(text("title", 480, 20, 720, 50,
                    "CHITCHAT Pipeline Architecture",
                    font_size=36, align="center"))
    els.append(text("subtitle", 480, 75, 720, 28,
                    "Boolean queries  ->  paper discovery  ->  AI screening  ->  analysis",
                    font_size=18, color="#525252", align="center"))

    # Lane geometry
    lane_x = 20
    lane_w = 1560
    lanes = [
        ("Stage 1\nBoolean Query\nGeneration", 130, C["zone1_fill"], C["zone1_stroke"],
         C["input_fill"], C["input_stroke"]),
        ("Stage 2\nPaper Discovery", 340, C["zone2_fill"], C["zone2_stroke"],
         C["script_fill"], C["script_stroke"]),
        ("Stage 3\nAI Screening", 550, C["zone3_fill"], C["zone3_stroke"],
         C["output_fill"], C["output_stroke"]),
        ("Stage 4\nAnalysis & Outputs", 760, C["zone4_fill"], C["zone4_stroke"],
         C["external_fill"], C["external_stroke"]),
    ]

    for i, (label, y_top, zone_fill, zone_stroke, lbl_fill, lbl_stroke) in enumerate(lanes):
        els.append(zone(f"z{i}", lane_x, y_top, lane_w, 190,
                        fill=zone_fill, stroke=zone_stroke))
        els.extend(labeled_box(f"l{i}", lane_x + 20, y_top + 35, 200, 120, label,
                               fill=lbl_fill, stroke=lbl_stroke,
                               font_size=20))

    # Helper to place node centered vertically in a lane
    def node_y(lane_top):
        return lane_top + 55, 90  # y, height (centered ~ lane_top+100)

    # ---------- Lane 1: Boolean Query Generation ----------
    y, h = node_y(130)
    nodes_l1 = [
        ("boolean.csv\nsynonym table", 260, 250),
        ("structure.json\nWORD + SYNONYMS", 560, 250),
        ("boolean_combinations.json\nOR groups per WORD", 870, 260),
        ("unique_boolean_combinations\n.json  (8 AND queries)", 1200, 320),
    ]
    arrow_labels_l1 = ["csv_to_json.py", "boolean_combinations.py",
                       "unique_boolean_combinations.py"]

    rect_ids = []
    for j, (lbl, x, w) in enumerate(nodes_l1):
        fill = C["output_fill"] if j == len(nodes_l1) - 1 else C["data_fill"]
        stroke = C["output_stroke"] if j == len(nodes_l1) - 1 else C["data_stroke"]
        els.extend(labeled_box(f"l1n{j}", x, y, w, h, lbl,
                               fill=fill, stroke=stroke, font_size=18))
        rect_ids.append((f"l1n{j}", x, w))

    for j in range(len(nodes_l1) - 1):
        x1 = rect_ids[j][1] + rect_ids[j][2]
        x2 = rect_ids[j + 1][1]
        arrow_x = x1 + 5
        arrow_dx = x2 - x1 - 10
        els.extend(arrow_with_label(
            f"l1a{j}", arrow_x, y + h / 2, arrow_dx, 0,
            arrow_labels_l1[j], font_size=14))

    # ---------- Lane 2: Paper Discovery ----------
    y, h = node_y(340)
    nodes_l2 = [
        ("unique_boolean\n_combinations.json", 260, 220, C["output_fill"], C["output_stroke"]),
        ("web_scrape.py +\narxiv_paper_search.py", 540, 230, C["script_fill"], C["script_stroke"]),
        ("External APIs\nOpenAlex / EuropePMC\narXiv / Google Scholar", 830, 240, C["external_fill"], C["external_stroke"]),
        ("PDF download +\nextract_paper_text\n(PyMuPDF / PyPDF2)", 1130, 240, C["script_fill"], C["script_stroke"]),
        ("papers.json\n(title, year, text)", 1410, 170, C["output_fill"], C["output_stroke"]),
    ]
    rect_ids = []
    for j, (lbl, x, w, fill, stroke) in enumerate(nodes_l2):
        els.extend(labeled_box(f"l2n{j}", x, y, w, h, lbl,
                               fill=fill, stroke=stroke, font_size=16))
        rect_ids.append((f"l2n{j}", x, w))

    arrow_labels_l2 = ["", "query", "PDFs", ""]
    for j in range(len(nodes_l2) - 1):
        x1 = rect_ids[j][1] + rect_ids[j][2]
        x2 = rect_ids[j + 1][1]
        arrow_x = x1 + 3
        arrow_dx = x2 - x1 - 6
        if arrow_labels_l2[j]:
            els.extend(arrow_with_label(
                f"l2a{j}", arrow_x, y + h / 2, arrow_dx, 0,
                arrow_labels_l2[j], font_size=14))
        else:
            els.append(arrow(f"l2a{j}", arrow_x, y + h / 2, arrow_dx, 0))

    # ---------- Lane 3: AI Screening ----------
    y, h = node_y(550)
    nodes_l3 = [
        ("papers.json", 260, 200, C["output_fill"], C["output_stroke"]),
        ("screen_papers.py\nfilter: year>=2020,\ntext>=500, dedupe", 510, 240, C["script_fill"], C["script_stroke"]),
        ("OpenAI gpt-5-mini\nstructured output", 800, 230, C["external_fill"], C["external_stroke"]),
        ("PaperScreening\n(Pydantic)\nquality + scope + ethics", 1080, 240, C["decision_fill"], C["decision_stroke"]),
        ("screening_results\n_*.jsonl", 1370, 200, C["output_fill"], C["output_stroke"]),
    ]
    rect_ids = []
    for j, (lbl, x, w, fill, stroke) in enumerate(nodes_l3):
        els.extend(labeled_box(f"l3n{j}", x, y, w, h, lbl,
                               fill=fill, stroke=stroke, font_size=16))
        rect_ids.append((f"l3n{j}", x, w))

    arrow_labels_l3 = ["", "prompt", "parse", "priority"]
    for j in range(len(nodes_l3) - 1):
        x1 = rect_ids[j][1] + rect_ids[j][2]
        x2 = rect_ids[j + 1][1]
        arrow_x = x1 + 3
        arrow_dx = x2 - x1 - 6
        if arrow_labels_l3[j]:
            els.extend(arrow_with_label(
                f"l3a{j}", arrow_x, y + h / 2, arrow_dx, 0,
                arrow_labels_l3[j], font_size=14))
        else:
            els.append(arrow(f"l3a{j}", arrow_x, y + h / 2, arrow_dx, 0))

    # ---------- Lane 4: Analysis ----------
    y_top = 760
    # Input box
    els.extend(labeled_box("l4n0", 260, 815, 230, 90,
                           "screening_results.jsonl\n+ scraped papers",
                           fill=C["output_fill"], stroke=C["output_stroke"],
                           font_size=16))
    # 3 parallel script boxes
    scripts = [
        ("paper_analysis.py", 760),
        ("web_scrape_analysis.py", 830),
        ("word_cloud_analysis.py", 900),
    ]
    for j, (lbl, sy) in enumerate(scripts):
        els.extend(labeled_box(f"l4s{j}", 590, sy, 300, 50, lbl,
                               fill=C["script_fill"], stroke=C["script_stroke"],
                               font_size=17))
    # Output
    els.extend(labeled_box("l4out", 990, 815, 560, 90,
                           "Plots  /  Dashboards  /  Word Clouds\n(priority distribution, scope, humanitarian scores)",
                           fill=C["result_fill"], stroke=C["result_stroke"],
                           font_size=16))
    # Arrows: input -> each script
    for j, (_, sy) in enumerate(scripts):
        els.append(arrow(f"l4a_in_{j}", 490, 860, 100, sy + 25 - 860))
    # Arrows: each script -> output
    for j, (_, sy) in enumerate(scripts):
        els.append(arrow(f"l4a_out_{j}", 890, sy + 25, 100, 860 - (sy + 25)))

    # ---------- Inter-stage flow arrows (right side, dashed blue) ----------
    flow_x = 1525
    flow_color = "#2563eb"
    els.append(arrow("f12", flow_x, 230, 0, 110, stroke=flow_color,
                     stroke_width=3, dashed=True))
    els.append(arrow("f23", flow_x, 440, 0, 110, stroke=flow_color,
                     stroke_width=3, dashed=True))
    # Stage 3 -> Stage 4: come back to the left because input is on left
    els.append(arrow("f34", flow_x, 650, -1050, 165, stroke=flow_color,
                     stroke_width=3, dashed=True))

    return els


# ---------------------------------------------------------------------------
# Diagram 2: Screening Schema (PaperScreening Pydantic)
# ---------------------------------------------------------------------------

def build_screening_schema():
    els = []

    els.append(text("title", 360, 20, 880, 50,
                    "AI Screening Schema  (screen_papers.py)",
                    font_size=32, align="center"))
    els.append(text("subtitle", 360, 72, 880, 28,
                    "OpenAI structured output  ->  PaperScreening (Pydantic)",
                    font_size=18, color="#525252", align="center"))

    # Left column: input -> filter -> prompt -> openai
    left_x = 60
    left_w = 280

    els.extend(labeled_box("input", left_x, 140, left_w, 110,
                           "papers.json entry\n{title, year, authors,\nextracted_text}",
                           fill=C["input_fill"], stroke=C["input_stroke"],
                           font_size=18))
    els.append(arrow("af1", left_x + left_w / 2, 250, 0, 50))

    els.extend(labeled_box("filter", left_x, 300, left_w, 140,
                           "Pre-filter\nyear >= 2020\nlen(text) >= 500\ndedupe by title-id",
                           fill=C["data_fill"], stroke=C["data_stroke"],
                           font_size=18))
    els.append(arrow("af2", left_x + left_w / 2, 440, 0, 50))

    els.extend(labeled_box("prompt", left_x, 490, left_w, 120,
                           "paper_screening_prompt.txt\n+ truncated text\n(first 60k chars)",
                           fill=C["external_fill"], stroke=C["external_stroke"],
                           font_size=17))
    els.append(arrow("af3", left_x + left_w / 2, 610, 0, 50))

    els.extend(labeled_box("openai", left_x, 660, left_w, 130,
                           "OpenAI gpt-5-mini\nbeta.chat.completions.parse\nresponse_format =\nPaperScreening",
                           fill=C["external_fill"], stroke=C["external_stroke"],
                           font_size=17))

    # Cross arrow to model box
    els.extend(arrow_with_label("toModel", left_x + left_w, 725, 100, -400,
                                "parses into",
                                stroke="#2563eb", stroke_width=3,
                                font_size=16))

    # Right side: PaperScreening container
    box_x = 460
    box_y = 130
    box_w = 1020
    box_h = 720
    els.append(zone("pcontainer", box_x, box_y, box_w, box_h,
                    fill=C["zone2_fill"], stroke=C["zone2_stroke"]))
    els.append(text("ptitle", box_x + 280, box_y + 15, 460, 32,
                    "PaperScreening (Pydantic Model)",
                    font_size=24, color="#5b21b6", align="center"))

    # 6 sub-models in a 3x2 grid
    sub_models = [
        ("PublicationQuality",
         "venue_name, is_top_tier_venue,\npublication_year, citation_count,\nis_recent_promising,\nfull_text_english"),
        ("TechnicalScope",
         "addresses_llm_data_collection\naddresses_text_corpus_creation\naddresses_web_scraping_nlp\naddresses_multilingual_compilation"),
        ("EthicalFlags",
         "focuses_only_on_performance\ndisregards_ethical_principles\nmissing_ethical_approval\nviolates_humanitarian_principles"),
        ("HumanitarianPrinciples",
         "humanity_score        0-3\nimpartiality_score   0-3\nindependence_score 0-3\nneutrality_score    0-3"),
        ("MethodologyContributions",
         "novel_methodology\nsystematic_evaluation\nreproducible_implementation"),
        ("EthicalContributions",
         "explicit_framework\nempirical_bias_analysis\nharm_mitigation_strategies\npolicy_recommendations\nacknowledges_tensions"),
    ]
    cell_w = 310
    cell_h = 175
    cell_xs = [box_x + 25, box_x + 360, box_x + 695]
    cell_ys = [box_y + 65, box_y + 260]
    for idx, (title_text, body) in enumerate(sub_models):
        col = idx % 3
        row = idx // 3
        x = cell_xs[col]
        y = cell_ys[row]
        # Header strip
        els.extend(labeled_box(f"sm{idx}_h", x, y, cell_w, 40, title_text,
                               fill=C["script_fill"], stroke=C["script_stroke"],
                               font_size=18))
        # Body
        els.extend(labeled_box(f"sm{idx}_b", x, y + 40, cell_w, cell_h - 40, body,
                               fill="#f3eaff", stroke=C["script_stroke"],
                               font_size=14))

    # Priority decision box
    prio_x = box_x + 165
    prio_y = box_y + 470
    prio_w = 700
    els.extend(labeled_box("prio", prio_x, prio_y, prio_w, 70,
                           "priority_level :  PriorityLevel   (LLM assigns)",
                           fill=C["decision_fill"], stroke=C["decision_stroke"],
                           font_size=20))

    # Arrows from each sub-model to the priority box
    for idx in range(6):
        col = idx % 3
        row = idx // 3
        x = cell_xs[col] + cell_w / 2
        y = cell_ys[row] + cell_h
        target_x = prio_x + prio_w / 2
        target_y = prio_y
        els.append(arrow(f"sma{idx}", x, y + 2, target_x - x, target_y - y - 4,
                         stroke="#7c3aed", stroke_width=1))

    # Priority levels (4 enum values)
    enum_y = box_y + 580
    enums = [
        ("HIGH PRIORITY", "#ffc9c9", "#dc2626"),
        ("MEDIUM PRIORITY", "#ffd8a8", "#c2410c"),
        ("LOW PRIORITY", "#fff3bf", "#a16207"),
        ("EXCLUDE", "#e5e5e5", "#525252"),
    ]
    enum_w = 200
    enum_gap = 30
    total_w = 4 * enum_w + 3 * enum_gap
    start_x = box_x + (box_w - total_w) / 2
    for j, (lbl, fill, stroke) in enumerate(enums):
        x = start_x + j * (enum_w + enum_gap)
        els.extend(labeled_box(f"e{j}", x, enum_y, enum_w, 70, lbl,
                               fill=fill, stroke=stroke, font_size=18))
        # Arrow from priority to enum
        a_start_x = prio_x + prio_w / 2
        a_start_y = prio_y + 70
        a_end_x = x + enum_w / 2
        a_end_y = enum_y
        els.append(arrow(f"ea{j}", a_start_x, a_start_y,
                         a_end_x - a_start_x, a_end_y - a_start_y - 4,
                         stroke="#a21caf", stroke_width=2))

    # Output box at right
    out_x = box_x + box_w + 30
    if out_x + 250 > 1620:
        out_x = box_x + box_w - 270  # fold inside if no space
    els.extend(labeled_box("out", 60, 830, 1480, 70,
                           "append_screening_result()   ->   output/screening_results_YYYYMMDD.jsonl",
                           fill=C["output_fill"], stroke=C["output_stroke"],
                           font_size=20))

    return els


# ---------------------------------------------------------------------------
# Diagram 3: Paper Discovery Module (standalone, API-ready)
# ---------------------------------------------------------------------------

def build_module_api():
    els = []

    # Title
    els.append(text("mtitle", 200, 20, 1200, 50,
                    "Paper Discovery Module  (standalone, API-ready)",
                    font_size=32, align="center"))
    els.append(text("msubtitle", 200, 75, 1200, 28,
                    "src/boolean + src/api bundled into one reusable service",
                    font_size=18, color="#525252", align="center"))

    # ---------- Consumers strip ----------
    els.append(zone("cz", 40, 120, 1520, 180,
                    fill=C["zone1_fill"], stroke=C["zone1_stroke"]))
    els.append(text("clbl", 60, 130, 700, 28,
                    "Consumer Applications  -  any project that needs literature",
                    font_size=18, color="#1d4ed8", align="left"))

    consumers = [
        "CHITCHAT screening\n(this project)",
        "Domain literature\nreviews",
        "Custom research\nprojects",
        "Notebooks /\nCLI / scripts",
    ]
    cons_x = [70, 430, 790, 1150]
    for j, lbl in enumerate(consumers):
        els.extend(labeled_box(f"c{j}", cons_x[j], 185, 320, 95, lbl,
                               fill=C["input_fill"], stroke=C["input_stroke"],
                               font_size=18))
        # Arrow from each consumer down into the module
        els.append(arrow(f"ca{j}", cons_x[j] + 160, 282, 0, 68,
                         stroke="#2563eb", stroke_width=2))

    # ---------- Module container ----------
    els.append(zone("mz", 40, 350, 1520, 640,
                    fill=C["zone2_fill"], stroke=C["zone2_stroke"]))
    els.append(text("mlbl", 60, 360, 800, 30,
                    "Paper Discovery Module",
                    font_size=22, color="#6d28d9", align="left"))
    els.append(text("mlbl2", 60, 390, 800, 20,
                    "Exposed via REST / Python library / CLI",
                    font_size=14, color="#525252", align="left"))

    # API surface row
    endpoints = [
        "POST  /search\nfull pipeline",
        "POST  /boolean-queries\nstep 1 only",
        "POST  /papers\nstep 2 only",
        "GET   /sources\nlist repositories",
    ]
    ep_x = [80, 440, 800, 1160]
    for j, lbl in enumerate(endpoints):
        els.extend(labeled_box(f"ep{j}", ep_x[j], 420, 340, 75, lbl,
                               fill=C["decision_fill"], stroke=C["decision_stroke"],
                               font_size=16))

    # ---------- Block 1: Boolean Query Builder ----------
    els.append(zone("b1z", 70, 515, 720, 380,
                    fill=C["zone1_fill"], stroke=C["zone1_stroke"]))
    els.append(text("b1lbl", 90, 528, 680, 28,
                    "1.  Boolean Query Builder",
                    font_size=20, color="#1d4ed8", align="left"))
    els.append(text("b1lbl2", 90, 558, 680, 20,
                    "Synonym table  ->  category-level boolean queries",
                    font_size=14, color="#525252", align="left"))

    b1_nodes = [
        ("Synonym input\nCSV  /  JSON", C["data_fill"], C["data_stroke"]),
        ("Query builder\ncsv_to_json\nboolean_combinations\nunique_boolean_combinations",
         C["script_fill"], C["script_stroke"]),
        ("8 boolean\ncategory queries", C["output_fill"], C["output_stroke"]),
    ]
    b1_x = [110, 320, 540]
    for j, (lbl, fill, stroke) in enumerate(b1_nodes):
        els.extend(labeled_box(f"b1n{j}", b1_x[j], 615, 180, 140, lbl,
                               fill=fill, stroke=stroke, font_size=14))
    els.append(arrow("b1a0", 290, 685, 30, 0))
    els.append(arrow("b1a1", 500, 685, 40, 0))

    els.append(text("b1note", 90, 775, 680, 60,
                    "Each WORD becomes an OR group of quoted synonyms.\nCategories combine multiple WORDs with AND.\nFully deterministic; no network calls.",
                    font_size=14, color="#525252", align="left"))

    # ---------- Block 2: Multi-Source Paper Fetch ----------
    els.append(zone("b2z", 810, 515, 720, 380,
                    fill=C["zone4_fill"], stroke=C["zone4_stroke"]))
    els.append(text("b2lbl", 830, 528, 680, 28,
                    "2.  Multi-Source Paper Fetch",
                    font_size=20, color="#c2410c", align="left"))
    els.append(text("b2lbl2", 830, 558, 680, 20,
                    "Federated search  ->  PDF download  ->  text extraction",
                    font_size=14, color="#525252", align="left"))

    # Dispatcher
    els.extend(labeled_box("b2disp", 830, 595, 680, 50,
                           "Query dispatcher  +  rate limiting  +  dedupe by title",
                           fill=C["script_fill"], stroke=C["script_stroke"],
                           font_size=15))

    # 4 source boxes
    sources = ["OpenAlex", "EuropePMC", "arXiv API", "Google Scholar"]
    src_x = [830, 1000, 1170, 1340]
    for j, lbl in enumerate(sources):
        els.extend(labeled_box(f"b2s{j}", src_x[j], 660, 160, 55, lbl,
                               fill=C["external_fill"],
                               stroke=C["external_stroke"], font_size=15))
        # Tiny vertical arrow from dispatcher to source
        els.append(arrow(f"b2da{j}", src_x[j] + 80, 645, 0, 15,
                         stroke_width=1))

    # PDF + extract
    els.extend(labeled_box("b2pdf", 830, 735, 680, 55,
                           "PDF download  +  extract_paper_text  (PyPDF2  /  PyMuPDF)",
                           fill=C["script_fill"], stroke=C["script_stroke"],
                           font_size=15))
    # Arrows from sources down to PDF box
    for j in range(4):
        els.append(arrow(f"b2sa{j}", src_x[j] + 80, 715, 0, 20,
                         stroke_width=1))

    els.append(text("b2note", 830, 800, 680, 40,
                    "Rate-limited per source.  Failures isolated;\npartial results returned with per-source status.",
                    font_size=14, color="#525252", align="left"))

    # Arrow connecting block 1 -> block 2 (queries flow)
    a_b1_b2 = arrow("b1to2", 790, 685, 22, 0,
                    stroke="#2563eb", stroke_width=3)
    tid = "b1to2_lbl"
    a_b1_b2["boundElements"] = [{"id": tid, "type": "text"}]
    els.append(a_b1_b2)
    els.append(text(tid, 770, 660, 60, 18, "queries",
                    font_size=14, container_id="b1to2"))

    # ---------- Module output bar ----------
    els.extend(labeled_box("mout", 70, 910, 1460, 65,
                           "papers.json   -   deduped, full-text papers   "
                           "{ title, authors, year, url, abstract, extracted_text }",
                           fill=C["output_fill"], stroke=C["output_stroke"],
                           font_size=17))

    return els


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    random.seed(42)

    pipeline = build_pipeline()
    schema = build_screening_schema()
    module = build_module_api()

    (OUT_DIR / "pipeline-architecture.excalidraw").write_text(
        json.dumps(wrap_file(pipeline), indent=2), encoding="utf-8"
    )
    (OUT_DIR / "screening-schema.excalidraw").write_text(
        json.dumps(wrap_file(schema), indent=2), encoding="utf-8"
    )
    (OUT_DIR / "paper-discovery-module.excalidraw").write_text(
        json.dumps(wrap_file(module), indent=2), encoding="utf-8"
    )
    print("Wrote pipeline-architecture.excalidraw")
    print("Wrote screening-schema.excalidraw")
    print("Wrote paper-discovery-module.excalidraw")


if __name__ == "__main__":
    main()
