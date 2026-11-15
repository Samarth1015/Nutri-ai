"""Generate the Nutri-AI SPM lab presentation (7 slides)."""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

# --- theme ---
FOREST = RGBColor(0x14, 0x32, 0x28)
LEAF = RGBColor(0x2D, 0x6A, 0x4F)
SAGE = RGBColor(0x40, 0x91, 0x6C)
MINT = RGBColor(0xD8, 0xF3, 0xDC)
CREAM = RGBColor(0xF6, 0xF8, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1C, 0x24, 0x22)
MUTED = RGBColor(0x5A, 0x6A, 0x64)
LINE = RGBColor(0xC9, 0xD6, 0xCE)
TERRACOTTA = RGBColor(0xB8, 0x5C, 0x38)
GOLD = RGBColor(0xC4, 0x8B, 0x3A)
SOFT_RED = RGBColor(0xF8, 0xE8, 0xE2)
SOFT_GOLD = RGBColor(0xFB, 0xF3, 0xE4)
SOFT_LEAF = RGBColor(0xE3, 0xF2, 0xEA)
NAVY_SOFT = RGBColor(0xE6, 0xEE, 0xF2)

SLIDE_W = 13.333
SLIDE_H = 7.5
TOTAL = 7


def _set_solid(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _set_line(shape, color, pt=1.0):
    shape.line.color.rgb = color
    shape.line.width = Pt(pt)


def _no_margin(tf):
    tf.word_wrap = True
    tf.auto_size = None
    inset = Emu(63500)  # ~0.07"
    tf._ttBody.set("lIns", str(inset))
    tf._ttBody.set("rIns", str(inset))
    tf._ttBody.set("tIns", str(inset))
    tf._ttBody.set("bIns", str(inset))


def add_run(paragraph, text, size, color, bold=False, font="Calibri", italic=False):
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    return run


def textbox(slide, l, t, w, h, text, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT, italic=False, font="Calibri", anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.paragraphs[0].alignment = align
    try:
        tf._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.clear()
    add_run(p, text, size, color, bold, font, italic)
    return box


def card(slide, l, t, w, h, fill=WHITE, line=LINE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    _set_solid(shape, fill)
    _set_line(shape, line, 1.0)
    # tighter corners
    try:
        shape.adjustments[0] = 0.08
    except Exception:
        pass
    return shape


def labeled_box(slide, l, t, w, h, fill, text, size=11, color=WHITE, bold=True, line=None, italic=False):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    _set_solid(shape, fill)
    if line:
        _set_line(shape, line, 1.0)
    else:
        shape.line.fill.background()
    try:
        shape.adjustments[0] = 0.12
    except Exception:
        pass
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    try:
        tf._txBody.bodyPr.set("anchor", "ctr")
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.clear()
    add_run(p, text, size, color, bold, italic=italic)
    return shape


def down_arrow(slide, cx, y, h=0.18, color=SAGE):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.DOWN_ARROW, Inches(cx - 0.09), Inches(y), Inches(0.18), Inches(h)
    )
    _set_solid(shape, color)
    return shape


def right_arrow(slide, l, t, w=0.22, h=0.12, color=SAGE):
    shape = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(l), Inches(t), Inches(w), Inches(h))
    _set_solid(shape, color)
    return shape


def add_bg(slide, color=CREAM):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SLIDE_W), Inches(SLIDE_H))
    _set_solid(bg, color)
    # send to back
    sp_tree = slide.shapes._spTree
    sp = bg._element
    sp_tree.remove(sp)
    sp_tree.insert(2, sp)
    return bg


def add_topbar(slide):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SLIDE_W), Inches(0.08))
    _set_solid(bar, LEAF)
    return bar


def add_header(slide, kicker, title):
    add_bg(slide)
    add_topbar(slide)
    textbox(slide, 0.55, 0.22, 10.5, 0.28, kicker.upper(), 11, SAGE, True)
    textbox(slide, 0.55, 0.46, 12.2, 0.46, title, 26, FOREST, True)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(0.98), Inches(1.4), Inches(0.045))
    _set_solid(rule, SAGE)


def add_footer(slide, page):
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(7.12), Inches(12.2), Inches(0.012))
    _set_solid(rule, LINE)
    textbox(slide, 0.55, 7.16, 8.5, 0.26, "Nutri-AI  ·  Software Project Management  ·  Lab Presentation", 10, MUTED)
    textbox(slide, 11.4, 7.16, 1.4, 0.26, f"{page}  /  {TOTAL}", 10, MUTED, align=PP_ALIGN.RIGHT)


def add_bullet_block(slide, l, t, w, h, items, size=15, color=INK, spacing=8):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(spacing)
        p.level = 0
        add_run(p, "●   ", size - 2, SAGE, True)
        add_run(p, item, size, color, False)
    return box


def numbered_items(slide, l, t, w, items, num_size=16, text_size=14, row_h=0.62, gap=0.08):
    for i, (title, body) in enumerate(items):
        y = t + i * (row_h + gap)
        badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(l), Inches(y + 0.06), Inches(0.36), Inches(0.36))
        _set_solid(badge, LEAF)
        tf = badge.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        try:
            tf._txBody.bodyPr.set("anchor", "ctr")
        except Exception:
            pass
        tf.paragraphs[0].clear()
        add_run(tf.paragraphs[0], str(i + 1), 12, WHITE, True)
        textbox(slide, l + 0.5, y, w - 0.5, 0.28, title, text_size, FOREST, True)
        if body:
            textbox(slide, l + 0.5, y + 0.26, w - 0.5, 0.34, body, 12, MUTED)


# ---------------------------------------------------------------------------
# Slides
# ---------------------------------------------------------------------------

def slide_intro(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # left panel
    left = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(5.05), Inches(SLIDE_H))
    _set_solid(left, FOREST)
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(5.05), Inches(0), Inches(0.08), Inches(SLIDE_H))
    _set_solid(accent, SAGE)

    right = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(5.13), Inches(0), Inches(8.21), Inches(SLIDE_H))
    _set_solid(right, CREAM)

    textbox(slide, 0.45, 0.42, 4.3, 0.28, "SOFTWARE PROJECT MANAGEMENT", 11, SAGE, True)
    textbox(slide, 0.45, 1.55, 4.3, 1.15, "Nutri-AI", 40, WHITE, True)
    textbox(slide, 0.45, 2.65, 4.3, 0.9, "WhatsApp-Native AI\nNutrition Assistant", 20, MINT, False)
    textbox(slide, 0.45, 5.35, 4.3, 0.28, "GROUP MEMBERS", 11, SAGE, True)
    textbox(slide, 0.45, 5.62, 4.3, 0.35, "Add names here", 14, RGBColor(0xA8, 0xC5, 0xB5), italic=True)
    textbox(
        slide,
        0.45,
        6.15,
        4.3,
        0.85,
        "Lab Presentation\nIntro → Problem → Aim → Solution → Flow → Method → References",
        12,
        RGBColor(0xA8, 0xC5, 0xB5),
    )

    textbox(slide, 5.6, 0.55, 7.2, 0.3, "01   INTRODUCTION", 12, SAGE, True)
    textbox(slide, 5.6, 0.9, 7.2, 0.5, "What this project is", 24, FOREST, True)

    intro = (
        "Nutri-AI (NutriCoach) is a WhatsApp-first multi-agent system that sits on the chat "
        "nutritionists already use. Clients log meals in natural language; the system stores "
        "structured nutrition data and lets coaches query progress in plain English."
    )
    textbox(slide, 5.6, 1.5, 7.2, 1.15, intro, 15, INK)

    add_bullet_block(
        slide,
        5.6,
        2.75,
        7.2,
        2.6,
        [
            "Clients text meals, workouts, and weight the way they already do on WhatsApp.",
            "An intake agent parses the message, looks up macros, and writes a meal log.",
            "A query agent answers the nutritionist: daily diet, missed logs, target updates.",
            "A scheduler can raise weekly compliance summaries without extra admin work.",
        ],
        size=14,
        spacing=10,
    )

    pill = labeled_box(
        slide,
        5.6,
        5.85,
        7.2,
        0.85,
        SOFT_LEAF,
        "Stack: FastAPI  ·  LangGraph  ·  MCP tools  ·  PostgreSQL  ·  Twilio WhatsApp  ·  Groq",
        13,
        FOREST,
        True,
        line=SAGE,
    )
    textbox(slide, 11.55, 7.12, 1.4, 0.26, "1  /  7", 10, MUTED, align=PP_ALIGN.RIGHT)


def slide_problem(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "02   Research / Industry Problem", "Why this problem exists")
    add_footer(slide, 2)

    # statement card
    card(slide, 0.55, 1.22, 12.2, 1.45, SOFT_RED, TERRACOTTA)
    textbox(slide, 0.75, 1.32, 11.8, 0.28, "PROBLEM STATEMENT", 11, TERRACOTTA, True)
    textbox(
        slide,
        0.75,
        1.62,
        11.8,
        0.9,
        "Nutritionists waste hours reconciling unstructured WhatsApp diet updates and spreadsheets, "
        "with no reliable way to log meals, monitor compliance, or query client progress in real time.",
        16,
        INK,
    )

    points = [
        ("Scattered chats", "Meal updates live in long WhatsApp threads. There is no single source of truth per client or per day."),
        ("Manual spreadsheets", "Coaches re-type foods, guess portions, and compute calories by hand — slow, inconsistent, and easy to miss."),
        ("No live compliance", "It is hard to see who skipped logs, who missed protein, or how a client did this week without opening every chat."),
        ("Tool fatigue", "A new diet app fails because clients and coaches already work on WhatsApp. Extra apps do not get used."),
    ]
    for i, (title, body) in enumerate(points):
        col = i % 2
        row = i // 2
        x = 0.55 + col * 6.2
        y = 2.88 + row * 1.95
        card(slide, x, y, 5.95, 1.8, WHITE, LINE)
        badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.2), Inches(y + 0.22), Inches(0.42), Inches(0.32))
        _set_solid(badge, TERRACOTTA if i < 2 else LEAF)
        try:
            badge.adjustments[0] = 0.2
        except Exception:
            pass
        tf = badge.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        try:
            tf._txBody.bodyPr.set("anchor", "ctr")
        except Exception:
            pass
        tf.paragraphs[0].clear()
        add_run(tf.paragraphs[0], f"0{i+1}", 10, WHITE, True)
        textbox(slide, x + 0.75, y + 0.2, 4.95, 0.35, title, 16, FOREST, True)
        textbox(slide, x + 0.22, y + 0.7, 5.5, 0.9, body, 13, MUTED)


def slide_aim(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "03   Aim and Objectives", "What we set out to do")
    add_footer(slide, 3)

    card(slide, 0.55, 1.22, 12.2, 1.35, SOFT_LEAF, SAGE)
    textbox(slide, 0.75, 1.32, 11.8, 0.26, "AIM", 11, LEAF, True)
    textbox(
        slide,
        0.75,
        1.62,
        11.8,
        0.8,
        "To design and develop a WhatsApp-native AI system that converts unstructured client diet "
        "chats into structured nutrition logs and lets nutritionists monitor compliance and query "
        "progress in real time — without leaving WhatsApp.",
        15,
        INK,
    )

    textbox(slide, 0.55, 2.75, 12.2, 0.35, "OBJECTIVES", 12, SAGE, True)

    objectives = [
        ("Capture meals from natural language", "Parse client WhatsApp texts into structured items (food, quantity, meal type, workout, weight)."),
        ("Enrich and persist nutrition data", "Look up calories, protein, carbs, and fat; store raw message + parsed JSON + daily totals."),
        ("Make progress queryable in plain language", "Let the nutritionist ask about a client, a day, missed logs, or targets and get a usable reply."),
        ("Flag gaps and summarise the week", "Detect missed logs and target misses; support weekly compliance summaries."),
        ("Route every sender automatically", "Identify client vs nutritionist vs unknown and send the message to the correct agent."),
    ]
    numbered_items(slide, 0.55, 3.15, 12.2, objectives, row_h=0.68, gap=0.06)


def slide_solution(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "04   How We Solve It", "Proposed solution")
    add_footer(slide, 4)

    textbox(
        slide,
        0.55,
        1.18,
        12.2,
        0.55,
        "Stay on WhatsApp. Turn chat into data. Let a small set of agents do the admin work.",
        16,
        INK,
    )

    pillars = [
        ("No new app", "Clients and coaches keep using WhatsApp. Twilio delivers the message to our webhook."),
        ("Four agents", "Intake logs meals. Query answers the coach. General handles unknown numbers. Report runs weekly."),
        ("Tools, not guesswork", "MCP tools write and read PostgreSQL and call FatSecret for macros, so answers are grounded in stored logs."),
        ("Structured memory", "Each log keeps the raw text, parsed meals, and totals — so later queries and weekly summaries are reliable."),
    ]
    for i, (title, body) in enumerate(pillars):
        x = 0.55 + i * 3.15
        card(slide, x, 1.85, 3.0, 2.15, WHITE, LINE)
        num = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.18), Inches(2.02), Inches(0.34), Inches(0.34))
        _set_solid(num, LEAF)
        tf = num.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        try:
            tf._txBody.bodyPr.set("anchor", "ctr")
        except Exception:
            pass
        tf.paragraphs[0].clear()
        add_run(tf.paragraphs[0], str(i + 1), 12, WHITE, True)
        textbox(slide, x + 0.18, 2.45, 2.64, 0.4, title, 16, FOREST, True)
        textbox(slide, x + 0.18, 2.88, 2.64, 0.95, body, 12, MUTED)

    # two columns: client vs coach
    card(slide, 0.55, 4.2, 6.0, 2.7, WHITE, LINE)
    labeled_box(slide, 0.75, 4.38, 2.15, 0.36, LEAF, "FOR THE CLIENT", 11, WHITE, True)
    add_bullet_block(
        slide,
        0.75,
        4.88,
        5.55,
        1.85,
        [
            "“today I ate 2 eggs and rice” → logged with macros",
            "Weight and workout notes are stored on the same day",
            "Friendly confirmation comes back on WhatsApp",
        ],
        size=13,
        spacing=8,
    )

    card(slide, 6.75, 4.2, 6.0, 2.7, WHITE, LINE)
    labeled_box(slide, 6.95, 4.38, 2.85, 0.36, FOREST, "FOR THE NUTRITIONIST", 11, WHITE, True)
    add_bullet_block(
        slide,
        6.95,
        4.88,
        5.55,
        1.85,
        [
            "“what did Shiva eat today” / “list my clients”",
            "“who has not logged in 3 days”",
            "“update Alice calories to 1800, protein to 120”",
        ],
        size=13,
        spacing=8,
    )


def slide_flowchart(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "05   System Flowchart", "Message path from WhatsApp to reply")
    add_footer(slide, 5)

    # row 1 — entry
    y1 = 1.22
    labeled_box(slide, 0.55, y1, 2.7, 0.62, FOREST, "Client / Coach\nWhatsApp", 11, WHITE)
    right_arrow(slide, 3.32, y1 + 0.25)
    labeled_box(slide, 3.62, y1, 2.55, 0.62, LEAF, "Twilio Gateway", 12, WHITE)
    right_arrow(slide, 6.24, y1 + 0.25)
    labeled_box(slide, 6.54, y1, 2.85, 0.62, LEAF, "FastAPI Webhook", 12, WHITE)
    right_arrow(slide, 9.46, y1 + 0.25)
    labeled_box(slide, 9.76, y1, 2.95, 0.62, SAGE, "Identify Sender\nclient / coach / unknown", 11, WHITE)

    down_arrow(slide, 6.66, 1.90, 0.18)

    # supervisor
    labeled_box(slide, 3.85, 2.14, 5.6, 0.55, FOREST, "LangGraph Supervisor  —  routes by sender type", 13, WHITE)

    down_arrow(slide, 6.66, 2.74, 0.16)

    # agents
    y3 = 2.96
    agents = [
        (0.55, LEAF, "Intake Agent", "Client meals, weight,\nworkout → log_meal"),
        (3.72, SAGE, "Query Agent", "Coach questions,\ntargets, compliance"),
        (6.89, RGBColor(0x3D, 0x5A, 0x80), "General Agent", "Unknown number\nor general help"),
        (10.06, GOLD, "Report Agent", "Weekly job\n(APScheduler)"),
    ]
    for x, color, title, sub in agents:
        labeled_box(slide, x, y3, 2.95, 0.48, color, title, 13, WHITE)
        labeled_box(slide, x, y3 + 0.52, 2.95, 0.62, WHITE, sub, 11, MUTED, False, line=LINE)

    down_arrow(slide, 6.66, 4.16, 0.16)

    labeled_box(
        slide,
        0.55,
        4.38,
        12.2,
        0.58,
        SOFT_LEAF,
        "MCP tools   ·   log_meal   ·   lookup_food_nutrition   ·   query_client_logs   ·   flag_nutritional_gaps   ·   list_clients_missing_logs",
        13,
        FOREST,
        True,
        line=SAGE,
    )

    down_arrow(slide, 6.66, 5.02, 0.16)

    labeled_box(slide, 0.55, 5.24, 5.95, 0.62, FOREST, "PostgreSQL   ·   client  ·  meal_log  ·  weekly_report", 13, WHITE)
    right_arrow(slide, 6.62, 5.48, 0.28, 0.14)
    labeled_box(slide, 7.02, 5.24, 5.73, 0.62, LEAF, "Twilio reply back to WhatsApp", 13, WHITE)

    textbox(
        slide,
        0.55,
        6.05,
        12.2,
        0.85,
        "Client path: message → intake → nutrition lookup (FatSecret) → meal_log → confirmation.   "
        "Coach path: message → query → MCP read/update → formatted answer.   "
        "Report path: Sunday scheduler → weekly summary for each client.",
        12,
        MUTED,
    )


def slide_method(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "06   Methodology", "How the system is built")
    add_footer(slide, 6)

    steps = [
        ("Study the workflow", "Map how a nutritionist already collects meals, checks compliance, and answers clients on WhatsApp."),
        ("Design the data and agents", "Schema: nutritionist, client (macro targets), meal_log, weekly_report. Four agents behind one supervisor."),
        ("Expose work as MCP tools", "Database writes/reads and FatSecret lookup are tools. Agents call tools; they do not invent totals."),
        ("Implement the pipeline", "FastAPI webhook → identify sender → LangGraph → Groq ReAct agent → Twilio reply."),
        ("Validate the two main paths", "Client meal + weight log; nutritionist list/query/update/missing-log questions."),
        ("Schedule and observe", "APScheduler for weekly reports; optional LangSmith traces for agent decisions."),
    ]

    for i, (title, body) in enumerate(steps):
        col = i % 3
        row = i // 3
        x = 0.55 + col * 4.15
        y = 1.22 + row * 2.15
        card(slide, x, y, 3.98, 2.0, WHITE, LINE)
        badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.2), Inches(y + 0.22), Inches(0.4), Inches(0.4))
        _set_solid(badge, LEAF)
        tf = badge.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        try:
            tf._txBody.bodyPr.set("anchor", "ctr")
        except Exception:
            pass
        tf.paragraphs[0].clear()
        add_run(tf.paragraphs[0], str(i + 1), 13, WHITE, True)
        textbox(slide, x + 0.72, y + 0.26, 3.05, 0.36, title, 15, FOREST, True)
        textbox(slide, x + 0.22, y + 0.78, 3.54, 1.05, body, 13, MUTED)

    # tech chips row is already covered in cards; add a thin strip if space - the 2x3 grid uses up to 5.37
    # y = 1.22 + 2.15 + 2.0 = 5.37, footer at 7.12 — room for a stack strip
    labeled_box(
        slide,
        0.55,
        5.62,
        12.2,
        0.55,
        FOREST,
        "Implementation stack:  FastAPI + Uvicorn   ·   LangGraph / LangChain   ·   ChatGroq   ·   FastMCP   ·   PostgreSQL + Alembic   ·   Twilio   ·   FatSecret   ·   APScheduler",
        12,
        WHITE,
        True,
    )


def slide_refs(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_header(slide, "07   References", "Sources used for the problem and the method")
    add_footer(slide, 7)

    refs = [
        "Thompson, F. E., & Subar, A. F. (2017). Dietary assessment methodology. In Nutrition in the Prevention and Treatment of Disease (4th ed.). Academic Press.",
        "Helander, E., Kaipainen, K., Korhonen, I., & Wansink, B. (2014). Factors related to sustained use of a free mobile app for dietary self-monitoring. Journal of Medical Internet Research, 16(10), e214.",
        "Mars, M., & Scott, R. E. (2016). WhatsApp in clinical practice: A literature review. Studies in Health Technology and Informatics, 231, 82–90.",
        "LangChain. (2024). LangGraph: Stateful multi-agent applications. https://langchain-ai.github.io/langgraph/",
        "Anthropic. (2024). Model Context Protocol specification. https://modelcontextprotocol.io/",
        "FatSecret. Platform API documentation. https://platform.fatsecret.com/   ·   Twilio. WhatsApp Business API. https://www.twilio.com/docs/whatsapp",
    ]

    for i, ref in enumerate(refs):
        y = 1.22 + i * 0.78
        card(slide, 0.55, y, 12.2, 0.7, WHITE, LINE)
        badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.72), Inches(y + 0.17), Inches(0.36), Inches(0.36))
        _set_solid(badge, LEAF)
        tf = badge.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        try:
            tf._txBody.bodyPr.set("anchor", "ctr")
        except Exception:
            pass
        tf.paragraphs[0].clear()
        add_run(tf.paragraphs[0], str(i + 1), 11, WHITE, True)
        textbox(slide, 1.25, y + 0.12, 11.25, 0.5, ref, 13, INK)

    textbox(slide, 0.55, 6.55, 12.2, 0.4, "Thank you  ·  Questions welcome", 16, FOREST, True, align=PP_ALIGN.CENTER)


def main():
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)

    slide_intro(prs)
    slide_problem(prs)
    slide_aim(prs)
    slide_solution(prs)
    slide_flowchart(prs)
    slide_method(prs)
    slide_refs(prs)

    out = r"d:\nutri-ai\presentation\NutriAI_SPM_Presentation.pptx"
    prs.save(out)
    print(out)


if __name__ == "__main__":
    main()
