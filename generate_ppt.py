"""
Generate a professional technical presentation for AI Photo Sharing project.
Run: python generate_ppt.py
Output: AI_Photo_Sharing_Presentation.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

# ─── Color Palette ───
BG_DARK      = RGBColor(0x0F, 0x17, 0x2A)   # Deep navy
BG_CARD      = RGBColor(0x16, 0x21, 0x3E)   # Card background
ACCENT_BLUE  = RGBColor(0x38, 0xBD, 0xF8)   # Bright cyan
ACCENT_PURPLE= RGBColor(0xA7, 0x8B, 0xFA)   # Soft purple
ACCENT_GREEN = RGBColor(0x4A, 0xDE, 0x80)   # Success green
ACCENT_ORANGE= RGBColor(0xFB, 0x92, 0x3C)   # Warning orange
ACCENT_PINK  = RGBColor(0xF4, 0x72, 0xB6)   # Pink highlight
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY   = RGBColor(0xCC, 0xCC, 0xCC)
MEDIUM_GRAY  = RGBColor(0x94, 0xA3, 0xB8)   # Muted text
DIM_WHITE    = RGBColor(0xE2, 0xE8, 0xF0)   # Slightly dimmed white

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)

SLIDE_W = prs.slide_width
SLIDE_H = prs.slide_height

# ─── Helper Functions ───

def add_dark_bg(slide):
    """Fill the entire slide with dark navy background."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG_DARK

def add_accent_bar(slide, color=ACCENT_BLUE, y=Inches(1.8), width=Inches(2.0)):
    """Add a thin accent underline bar."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.9), y, width, Pt(4)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()

def add_text_box(slide, left, top, width, height, text, font_size=18,
                 color=WHITE, bold=False, alignment=PP_ALIGN.LEFT, font_name="Segoe UI"):
    """Add a styled text box."""
    txbox = slide.shapes.add_textbox(left, top, width, height)
    tf = txbox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txbox

def add_bullet_list(slide, left, top, width, height, items, font_size=16,
                    color=DIM_WHITE, bullet_color=ACCENT_BLUE, spacing=Pt(8)):
    """Add a bulleted list with colored bullet markers."""
    txbox = slide.shapes.add_textbox(left, top, width, height)
    tf = txbox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.space_after = spacing

        # Bullet marker
        run_bullet = p.add_run()
        run_bullet.text = "▸ "
        run_bullet.font.size = Pt(font_size)
        run_bullet.font.color.rgb = bullet_color
        run_bullet.font.name = "Segoe UI"
        run_bullet.font.bold = True

        # Item text
        run_text = p.add_run()
        run_text.text = item
        run_text.font.size = Pt(font_size)
        run_text.font.color.rgb = color
        run_text.font.name = "Segoe UI"
    return txbox

def add_card(slide, left, top, width, height, title, items,
             accent_color=ACCENT_BLUE, title_size=18, item_size=14):
    """Add a card-like box with title and bullet items."""
    # Card background
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = BG_CARD
    card.line.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    card.line.width = Pt(1)
    # Accent top bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left + Inches(0.15), top + Inches(0.1), Inches(0.8), Pt(3)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_color
    bar.line.fill.background()

    # Title
    add_text_box(slide, left + Inches(0.15), top + Inches(0.25), width - Inches(0.3), Inches(0.4),
                 title, font_size=title_size, color=accent_color, bold=True)

    # Items
    add_bullet_list(slide, left + Inches(0.15), top + Inches(0.7), width - Inches(0.3),
                    height - Inches(0.9), items, font_size=item_size, color=DIM_WHITE,
                    bullet_color=accent_color, spacing=Pt(5))

def add_flow_arrow(slide, left, top, width=Inches(0.8), color=ACCENT_BLUE):
    """Add a horizontal arrow shape."""
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW, left, top, width, Inches(0.4)
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = color
    arrow.line.fill.background()

def add_down_arrow(slide, left, top, height=Inches(0.6), color=ACCENT_BLUE):
    """Add a vertical down arrow shape."""
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.DOWN_ARROW, left, top, Inches(0.4), height
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = color
    arrow.line.fill.background()

def add_slide_number(slide, num, total):
    """Add slide number at bottom right."""
    add_text_box(slide, Inches(11.8), Inches(7.0), Inches(1.3), Inches(0.4),
                 f"{num} / {total}", font_size=10, color=MEDIUM_GRAY,
                 alignment=PP_ALIGN.RIGHT)

TOTAL_SLIDES = 15

# ═══════════════════════════════════════════
# SLIDE 1 — TITLE SLIDE
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
add_dark_bg(slide)

# Large gradient-like accent shape behind title
rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), SLIDE_W, Inches(0.15))
rect.fill.solid()
rect.fill.fore_color.rgb = ACCENT_BLUE
rect.line.fill.background()

add_text_box(slide, Inches(0.9), Inches(1.5), Inches(11), Inches(1.2),
             "AI Photo Sharing Platform", font_size=46, color=WHITE, bold=True)

add_accent_bar(slide, ACCENT_BLUE, y=Inches(2.8), width=Inches(3.0))

add_text_box(slide, Inches(0.9), Inches(3.2), Inches(11), Inches(0.8),
             "Intelligent Face Recognition & Automated Photo Distribution",
             font_size=24, color=MEDIUM_GRAY, bold=False)

add_text_box(slide, Inches(0.9), Inches(4.5), Inches(5), Inches(0.5),
             "InsightFace (buffalo_l)  ·  Flask  ·  Supabase  ·  Hugging Face  ·  Docker",
             font_size=14, color=ACCENT_PURPLE, bold=False)

add_text_box(slide, Inches(0.9), Inches(5.6), Inches(5), Inches(0.5),
             "Technical Deep Dive  |  June 2026",
             font_size=16, color=DIM_WHITE, bold=False)

add_text_box(slide, Inches(0.9), Inches(6.2), Inches(5), Inches(0.4),
             "GitHub: himansh478/ai-photosharing", font_size=13, color=ACCENT_GREEN)
add_text_box(slide, Inches(0.9), Inches(6.55), Inches(5), Inches(0.4),
             "Live: gour-himansh.hf.space", font_size=13, color=ACCENT_GREEN)

add_slide_number(slide, 1, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 2 — PROBLEM & SOLUTION
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Problem & Solution", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PINK, y=Inches(1.2))

# Problem card
add_card(slide, Inches(0.9), Inches(1.8), Inches(5.5), Inches(2.5),
         "❌  THE PROBLEM", [
             "Event photos manually sorted by photographer",
             "Users scroll through 100s of photos to find themselves",
             "No automated face-matching at scale",
             "Photo distribution is slow, expensive & error-prone"
         ], accent_color=ACCENT_ORANGE, title_size=17, item_size=15)

# Solution card
add_card(slide, Inches(6.9), Inches(1.8), Inches(5.5), Inches(2.5),
         "✅  OUR SOLUTION", [
             "AI-powered face detection + 512-dim embedding extraction",
             "User uploads selfie → instant face match across event gallery",
             "Cosine similarity search (threshold 0.4) for high recall",
             "Fully automated — zero manual sorting needed"
         ], accent_color=ACCENT_GREEN, title_size=17, item_size=15)

# How it works summary
add_card(slide, Inches(0.9), Inches(4.7), Inches(11.5), Inches(2.2),
         "🔄  HOW IT WORKS (In 4 Steps)", [
             "1. Photographer registers event & gets unique code (EVT-2026-XXXXXX)",
             "2. Photographer uploads batch photos → AI detects faces & generates 512-dim embeddings → stored in Supabase (JSONB)",
             "3. User enters event code + uploads selfie → AI extracts user's face embedding",
             "4. System runs cosine similarity against all event embeddings → returns matched photos instantly"
         ], accent_color=ACCENT_BLUE, title_size=17, item_size=15)

add_slide_number(slide, 2, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 3 — TECH STACK OVERVIEW
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Technology Stack", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PURPLE, y=Inches(1.2))

cards = [
    ("🧠  AI / ML", [
        "InsightFace (buffalo_l) — ONNX model",
        "Face Detection + 512-dim Embedding",
        "OpenCV (headless) for image I/O",
        "NumPy / SciPy — cosine similarity"
    ], ACCENT_BLUE),
    ("⚙️  Backend", [
        "Flask 2.3 (Python 3.10)",
        "Waitress WSGI (Production server)",
        "Blueprint-based modular API",
        "ThreadPoolExecutor + Semaphore"
    ], ACCENT_GREEN),
    ("🗄️  Database", [
        "Supabase (PostgreSQL 15+)",
        "ThreadedConnectionPool (psycopg2)",
        "JSONB for face embeddings storage",
        "Row Level Security (RLS) enabled"
    ], ACCENT_PURPLE),
    ("☁️  Cloud & Storage", [
        "Hugging Face Datasets (private repo)",
        "Secure Proxy API (token never exposed)",
        "Docker multi-stage build",
        "HF Spaces (free tier deployment)"
    ], ACCENT_ORANGE),
]

for i, (title, items, color) in enumerate(cards):
    col = i % 4
    x = Inches(0.5) + col * Inches(3.15)
    y = Inches(1.7)
    add_card(slide, x, y, Inches(2.95), Inches(3.5), title, items,
             accent_color=color, title_size=15, item_size=12)

# Additional tech row
add_card(slide, Inches(0.5), Inches(5.5), Inches(5.8), Inches(1.5),
         "🛡️  Security & Monitoring", [
             "Strict CORS (domain whitelist)",
             "CSP headers (anti-iframe hijack)",
             "Flask-Limiter (rate limiting: 5/min on verify)",
             "Sentry SDK (error monitoring in production)"
         ], accent_color=ACCENT_PINK, title_size=14, item_size=12)

add_card(slide, Inches(6.7), Inches(5.5), Inches(5.8), Inches(1.5),
         "🧪  Testing & DevOps", [
             "Pytest unit tests (user endpoints, matching)",
             "Config.TESTING flag (skip heavy engine load)",
             "Docker healthcheck endpoint (/api/health)",
             "GitHub Push Protection (secret scanning)"
         ], accent_color=ACCENT_BLUE, title_size=14, item_size=12)

add_slide_number(slide, 3, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 4 — SYSTEM ARCHITECTURE
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "System Architecture", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_BLUE, y=Inches(1.2))

# Row 1: Frontend
add_card(slide, Inches(0.5), Inches(1.6), Inches(3.5), Inches(1.6),
         "🌐 Frontend (Static HTML/JS)", [
             "Landing Page (/)",
             "Photographer Dashboard (/photographer)",
             "User Face Match Portal (/user)"
         ], accent_color=ACCENT_BLUE, title_size=14, item_size=12)

add_flow_arrow(slide, Inches(4.1), Inches(2.2), Inches(0.7), ACCENT_BLUE)

# Flask API
add_card(slide, Inches(4.9), Inches(1.6), Inches(3.5), Inches(1.6),
         "⚙️ Flask API (Waitress)", [
             "photographer_bp  (register, upload-batch, stats)",
             "user_bp  (verify-code, upload-selfie, download)",
             "Proxy endpoint  (/api/proxy/*)"
         ], accent_color=ACCENT_GREEN, title_size=14, item_size=12)

add_flow_arrow(slide, Inches(8.5), Inches(2.2), Inches(0.7), ACCENT_GREEN)

# InsightFace
add_card(slide, Inches(9.3), Inches(1.6), Inches(3.5), Inches(1.6),
         "🧠 InsightFace Engine", [
             "FaceAnalysis (buffalo_l, ONNX)",
             "detect_and_embed() → list[512-dim]",
             "get_user_embedding() → best face",
         ], accent_color=ACCENT_PURPLE, title_size=14, item_size=12)

# Row 2: Data layer
add_down_arrow(slide, Inches(6.4), Inches(3.3), Inches(0.5), ACCENT_GREEN)

add_card(slide, Inches(0.5), Inches(4.1), Inches(3.8), Inches(2.8),
         "🗄️ Supabase (PostgreSQL)", [
             "photographers — event registration",
             "photos — file_path, embeddings (JSONB)",
             "user_sessions — selfie + match count",
             "download_logs — audit trail",
             "ThreadedConnectionPool (1-20 conns)",
             "Auto-retry with pooler fallback"
         ], accent_color=ACCENT_PURPLE, title_size=14, item_size=12)

add_card(slide, Inches(4.6), Inches(4.1), Inches(3.8), Inches(2.8),
         "☁️ Hugging Face (Private Dataset)", [
             "photos/ — full resolution originals",
             "thumbnails/ — 400×400 JPEG (quality 85)",
             "HfApi.upload_file() with Bearer token",
             "Proxy API: /api/proxy/<path>",
             "Token NEVER exposed to frontend",
             "Stream response (4KB chunks)"
         ], accent_color=ACCENT_ORANGE, title_size=14, item_size=12)

add_card(slide, Inches(8.7), Inches(4.1), Inches(3.8), Inches(2.8),
         "🔍 Matching Service", [
             "Fetch all photos for photographer_id",
             "json_to_embeddings() → numpy arrays",
             "Cosine similarity (np.dot / norms)",
             "Threshold ≥ 0.4 → match confirmed",
             "Sort by similarity DESC",
             "Return photo_id + thumbnail + download URL"
         ], accent_color=ACCENT_PINK, title_size=14, item_size=12)

add_slide_number(slide, 4, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 5 — AI FACE ENGINE DEEP DIVE
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "AI Face Engine — Deep Dive", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PURPLE, y=Inches(1.2))

add_text_box(slide, Inches(0.9), Inches(1.5), Inches(11), Inches(0.6),
             "File: backend/models/face_engine.py  |  Class: FaceEngine  |  Pattern: Singleton (get_engine())",
             font_size=13, color=MEDIUM_GRAY)

add_card(slide, Inches(0.5), Inches(2.2), Inches(3.8), Inches(4.8),
         "📦  Model Loading (_load)", [
             "Library: insightface.app.FaceAnalysis",
             "Model: buffalo_l (ArcFace + RetinaFace)",
             "Format: ONNX Runtime execution",
             "det_size: (640, 640) — OOM-safe for HF",
             "det_thresh: 0.35 — balanced recall/precision",
             "ctx_id: GPU (0) if torch.cuda else CPU (-1)",
             "Singleton pattern → loaded once globally",
             "Background thread loading → server starts fast",
             "Error captured in self.load_error"
         ], accent_color=ACCENT_PURPLE, title_size=16, item_size=13)

add_card(slide, Inches(4.6), Inches(2.2), Inches(3.8), Inches(4.8),
         "🔬  detect_and_embed(image_path)", [
             "Input: local file path (JPEG/PNG/WebP)",
             "Step 1: cv2.imread() → BGR numpy array",
             "Step 2: self._app.get(img) → list[Face]",
             "Step 3: face.normed_embedding → 512-dim vec",
             "Output: list[np.ndarray] — one per face",
             "Returns [] if no faces or engine not ready",
             "Used by: Photographer batch upload pipeline",
             "Face count stored in photos.face_count",
             "Photos with 0 faces → skipped (no upload)"
         ], accent_color=ACCENT_BLUE, title_size=16, item_size=13)

add_card(slide, Inches(8.7), Inches(2.2), Inches(3.8), Inches(4.8),
         "👤  get_user_embedding(image_path)", [
             "Input: user selfie file path",
             "Step 1: cv2.imread() → BGR array",
             "Step 2: self._app.get(img) → Face list",
             "Step 3: Pick largest face by bbox area:",
             "   max(faces, key=bbox_area)",
             "Step 4: Return normed_embedding (512-d)",
             "Returns None if no face detected",
             "Used by: User selfie upload endpoint",
             "Only ONE embedding → the most prominent face"
         ], accent_color=ACCENT_GREEN, title_size=16, item_size=13)

add_slide_number(slide, 5, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 6 — PHOTOGRAPHER UPLOAD FLOW
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Photographer Upload Pipeline", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_GREEN, y=Inches(1.2))

add_text_box(slide, Inches(0.9), Inches(1.5), Inches(11), Inches(0.5),
             "File: backend/api/photographer.py  |  Async batch processing with ThreadPoolExecutor",
             font_size=13, color=MEDIUM_GRAY)

# Step boxes in sequence
steps = [
    ("1️⃣  Register", "POST /api/photographer/register\n\nInput: name, email, event_name\nOutput: photographer_id + code\nCode format: EVT-2026-XXXXXX\nStored in: photographers table", ACCENT_BLUE),
    ("2️⃣  Upload Batch", "POST /api/photographer/upload-batch\n\nInput: code + photos[] (max 120)\nValidate photographer code\nSave all files to TEMP dir\nReturn job_id (HTTP 202 Accepted)", ACCENT_GREEN),
    ("3️⃣  AI Processing", "_process_batch() in background thread\n\nAI_SEMAPHORE (limit 1 concurrent)\nFor each photo:\n  → engine.detect_and_embed()\n  → Skip if no faces found\n  → Submit to UPLOAD_EXECUTOR", ACCENT_PURPLE),
    ("4️⃣  Cloud Upload", "_finish_upload() in ThreadPoolExecutor(5)\n\nupload_to_hf() → photos/ folder\ngenerate_thumbnail() → thumbnails/\nINSERT into photos table\nUPDATE photographer total_photos\nCleanup temp file", ACCENT_ORANGE),
]

for i, (title, desc, color) in enumerate(steps):
    x = Inches(0.4) + i * Inches(3.2)
    y = Inches(2.2)

    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(2.95), Inches(4.2))
    card.fill.solid()
    card.fill.fore_color.rgb = BG_CARD
    card.line.color.rgb = color
    card.line.width = Pt(2)

    add_text_box(slide, x + Inches(0.1), y + Inches(0.15), Inches(2.75), Inches(0.4),
                 title, font_size=16, color=color, bold=True)

    # Description text
    txbox = slide.shapes.add_textbox(x + Inches(0.1), y + Inches(0.65), Inches(2.75), Inches(3.4))
    tf = txbox.text_frame
    tf.word_wrap = True
    for line in desc.split('\n'):
        if tf.paragraphs[0].text == '':
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(11)
        p.font.color.rgb = DIM_WHITE
        p.font.name = "Segoe UI"
        p.space_after = Pt(2)

    # Arrow between steps
    if i < len(steps) - 1:
        add_flow_arrow(slide, x + Inches(3.0), y + Inches(1.8), Inches(0.15), color)

# Batch status endpoint
add_card(slide, Inches(0.5), Inches(6.6), Inches(12), Inches(0.7),
         "📊  GET /api/photographer/batch-status/<job_id>  →  {status, total, processed, uploaded, skipped}",
         [], accent_color=ACCENT_BLUE, title_size=13, item_size=11)

add_slide_number(slide, 6, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 7 — USER FACE MATCHING FLOW
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "User Face Matching Flow", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PINK, y=Inches(1.2))

add_text_box(slide, Inches(0.9), Inches(1.5), Inches(11), Inches(0.5),
             "Files: backend/api/user.py + backend/services/matching_service.py",
             font_size=13, color=MEDIUM_GRAY)

steps = [
    ("1️⃣ Verify Code", [
        "POST /api/user/verify-code",
        "Rate limited: 5 per minute",
        "Query photographers WHERE code=?",
        "Fallback: Supabase REST API if DB fails",
        "Returns: event_name, photographer info"
    ], ACCENT_BLUE),
    ("2️⃣ Upload Selfie", [
        "POST /api/user/upload-selfie",
        "Save selfie to temp dir",
        "engine.get_user_embedding(path)",
        "Pick largest face from selfie",
        "Returns 400 if no face detected",
        "Upload selfie to HF for persistence"
    ], ACCENT_GREEN),
    ("3️⃣ Face Matching", [
        "MatchingService.find_matches()",
        "SELECT all photos for photographer",
        "For each photo's embeddings:",
        "  → cosine_similarity(user, photo_face)",
        "  → Track best_sim across all faces",
        "Filter: best_sim >= 0.4 (threshold)",
        "Sort by similarity DESC"
    ], ACCENT_PURPLE),
    ("4️⃣ Results & Download", [
        "Create user_session in DB",
        "Return matched photos array:",
        "  { photo_id, thumbnail_url,",
        "    download_url, similarity }",
        "GET /api/user/download/<photo_id>",
        "Log download → redirect to cloud URL"
    ], ACCENT_ORANGE),
]

for i, (title, items, color) in enumerate(steps):
    x = Inches(0.4) + i * Inches(3.2)
    y = Inches(2.1)
    add_card(slide, x, y, Inches(2.95), Inches(4.5), title, items,
             accent_color=color, title_size=15, item_size=12)
    if i < len(steps) - 1:
        add_flow_arrow(slide, x + Inches(3.0), y + Inches(2.0), Inches(0.15), color)

add_slide_number(slide, 7, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 8 — DATABASE SCHEMA
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Database Schema (Supabase PostgreSQL)", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PURPLE, y=Inches(1.2))

add_text_box(slide, Inches(0.9), Inches(1.5), Inches(11), Inches(0.5),
             "File: backend/database/db.py  |  Auto-created via init_db()  |  ThreadedConnectionPool (1-20)",
             font_size=13, color=MEDIUM_GRAY)

tables = [
    ("📸  photographers", [
        "id  TEXT  PRIMARY KEY",
        "name  TEXT  NOT NULL",
        "email  TEXT  NOT NULL",
        "event_name  TEXT  NOT NULL",
        "code  TEXT  UNIQUE NOT NULL",
        "total_photos  INTEGER  DEFAULT 0",
        "created_at  TIMESTAMP"
    ], ACCENT_BLUE),
    ("🖼️  photos", [
        "id  TEXT  PRIMARY KEY",
        "photographer_id  TEXT  FK → photographers",
        "file_path  TEXT  (proxy URL)",
        "thumbnail_path  TEXT  (proxy URL)",
        "original_filename  TEXT",
        "face_count  INTEGER",
        "embeddings  JSONB  ← 512-dim vectors",
        "uploaded_at  TIMESTAMP"
    ], ACCENT_GREEN),
    ("👤  user_sessions", [
        "id  TEXT  PRIMARY KEY",
        "photographer_id  TEXT  FK → photographers",
        "selfie_path  TEXT",
        "matched_count  INTEGER",
        "created_at  TIMESTAMP"
    ], ACCENT_PURPLE),
    ("📥  download_logs", [
        "id  TEXT  PRIMARY KEY",
        "session_id  TEXT  FK → user_sessions",
        "photo_id  TEXT  FK → photos",
        "downloaded_at  TIMESTAMP"
    ], ACCENT_ORANGE),
]

for i, (title, items, color) in enumerate(tables):
    col = i % 2
    row = i // 2
    x = Inches(0.5) + col * Inches(6.2)
    y = Inches(2.0) + row * Inches(2.7)
    add_card(slide, x, y, Inches(5.9), Inches(2.5), title, items,
             accent_color=color, title_size=15, item_size=12)

add_slide_number(slide, 8, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 9 — COSINE SIMILARITY EXPLAINED
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Face Matching Algorithm — Cosine Similarity", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_BLUE, y=Inches(1.2))

add_card(slide, Inches(0.5), Inches(1.6), Inches(5.8), Inches(3.0),
         "📐  Mathematical Foundation", [
             "similarity(A, B) = (A · B) / (||A|| × ||B||)",
             "",
             "A = User selfie embedding (512-dimensional vector)",
             "B = Each face embedding from event photos",
             "Result range: -1.0 to 1.0 (1.0 = perfect match)",
             "",
             "InsightFace outputs normalized embeddings →",
             "  dot product ≈ cosine similarity directly",
         ], accent_color=ACCENT_BLUE, title_size=16, item_size=14)

add_card(slide, Inches(6.7), Inches(1.6), Inches(5.8), Inches(3.0),
         "⚡  Implementation (matching_service.py)", [
             "a = np.array(user_emb, dtype=float32).flatten()",
             "b = np.array(photo_emb, dtype=float32).flatten()",
             "norm_a = np.linalg.norm(a)",
             "norm_b = np.linalg.norm(b)",
             "similarity = np.dot(a, b) / (norm_a × norm_b)",
             "",
             "For each photo: track best_sim across all faces",
             "Match confirmed if best_sim ≥ 0.4",
         ], accent_color=ACCENT_GREEN, title_size=16, item_size=14)

# Threshold explanation
add_card(slide, Inches(0.5), Inches(5.0), Inches(12), Inches(2.2),
         "🎯  Threshold Configuration (Config.SIMILARITY_THRESHOLD = 0.4)", [
             "0.4 = Aggressive recall — catches more potential matches, may include a few false positives",
             "0.5 = Balanced — good precision/recall trade-off for most event scenarios",
             "0.6+ = Conservative — very high precision but may miss matches in poor lighting/angle conditions",
             "Why 0.4?  →  Events have varied lighting, angles, partial occlusions — higher recall is preferred over missed photos"
         ], accent_color=ACCENT_ORANGE, title_size=15, item_size=14)

add_slide_number(slide, 9, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 10 — CLOUD STORAGE (HF) ARCHITECTURE
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Cloud Storage — Hugging Face Architecture", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_ORANGE, y=Inches(1.2))

add_text_box(slide, Inches(0.9), Inches(1.5), Inches(11), Inches(0.5),
             "File: backend/services/upload_service.py  |  Secure Proxy: backend/app.py",
             font_size=13, color=MEDIUM_GRAY)

add_card(slide, Inches(0.5), Inches(2.1), Inches(3.8), Inches(4.5),
         "📤  Upload Flow", [
             "UploadService → HfApi instance",
             "save_photo(temp_path, filename):",
             "  → UUID hex filename (no collision)",
             "  → path_in_repo = photos/{uuid}.jpg",
             "  → api.upload_file() to private dataset",
             "  → Return: /api/proxy/photos/{uuid}.jpg",
             "",
             "generate_thumbnail(local_path):",
             "  → PIL Image.thumbnail(400×400, LANCZOS)",
             "  → Save JPEG quality=85",
             "  → Upload to thumbnails/ folder",
         ], accent_color=ACCENT_ORANGE, title_size=16, item_size=13)

add_card(slide, Inches(4.6), Inches(2.1), Inches(3.8), Inches(4.5),
         "🔒  Secure Proxy", [
             "GET /api/proxy/<filepath>",
             "",
             "Why proxy?",
             "  → HF_TOKEN is NEVER sent to frontend",
             "  → Client gets photos via our API only",
             "  → No direct HF URL exposure",
             "",
             "How it works:",
             "  → Build HF URL with Bearer token",
             "  → requests.get(url, stream=True)",
             "  → Stream 4KB chunks → Response",
             "  → Pass-through content-type header"
         ], accent_color=ACCENT_BLUE, title_size=16, item_size=13)

add_card(slide, Inches(8.7), Inches(2.1), Inches(3.8), Inches(4.5),
         "📁  Repository Structure", [
             "Repo: HF_DATASET_ID (private)",
             "Type: dataset (not model/space)",
             "",
             "photos/",
             "  ├── {uuid1}.jpg   (full-res)",
             "  ├── {uuid2}.png",
             "  └── ...",
             "",
             "thumbnails/",
             "  ├── thumb_{uuid1}.jpg  (400×400)",
             "  ├── thumb_{uuid2}.jpg",
             "  └── ...",
         ], accent_color=ACCENT_GREEN, title_size=16, item_size=13)

add_slide_number(slide, 10, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 11 — DATABASE CONNECTION STRATEGY
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Database Connection Strategy", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PURPLE, y=Inches(1.2))

add_card(slide, Inches(0.5), Inches(1.6), Inches(5.8), Inches(5.2),
         "🔄  Smart Connection Pool (init_pool)", [
             "Uses psycopg2.pool.ThreadedConnectionPool",
             "Min: 1 connection  |  Max: 20 connections",
             "",
             "Multi-endpoint fallback strategy:",
             "  1. Try user-configured DB URL first",
             "  2. Try Supabase Transaction Pooler (port 6543)",
             "  3. Try alternate port (5432 ↔ 6543)",
             "  4. Auto-detect pooler vs direct host",
             "",
             "IPv4 DNS resolution (bypass IPv6 issues):",
             "  → socket.gethostbyname() for hostaddr param",
             "  → Critical fix for Azure/HF Spaces networking",
             "",
             "SSL: require for pooler, prefer for direct",
             "GSS encryption: disabled (avoids Kerberos issues)"
         ], accent_color=ACCENT_PURPLE, title_size=16, item_size=13)

add_card(slide, Inches(6.7), Inches(1.6), Inches(5.8), Inches(5.2),
         "🛡️  Context Manager Pattern", [
             "@contextmanager",
             "def get_db_conn():",
             "    conn = _pool.getconn()",
             "    try:",
             "        # Health check: SELECT 1",
             "        yield conn",
             "    finally:",
             "        _pool.putconn(conn)  # Always return",
             "",
             "Benefits:",
             "  ✅ Auto-release on exception",
             "  ✅ Connection health check before use",
             "  ✅ Thread-safe pool access",
             "  ✅ No connection leaks possible",
             "  ✅ Supports concurrent batch processing"
         ], accent_color=ACCENT_GREEN, title_size=16, item_size=13)

add_slide_number(slide, 11, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 12 — DOCKER & DEPLOYMENT
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Docker & Deployment Architecture", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_BLUE, y=Inches(1.2))

add_card(slide, Inches(0.5), Inches(1.6), Inches(5.8), Inches(5.2),
         "🐳  Multi-Stage Dockerfile", [
             "STAGE 1: Builder (python:3.10-slim)",
             "  → Virtual environment: /opt/venv",
             "  → InsightFace prebuilt wheel (30s vs 15min!)",
             "  → pip install from requirements.txt",
             "",
             "STAGE 2: Runtime (python:3.10-slim)",
             "  → Only runtime libs: libgl1, libglib2.0",
             "  → COPY --from=builder /opt/venv",
             "  → App source code COPY",
             "  → Writable dirs: models_cache, storage/temp",
             "",
             "Key optimizations:",
             "  ✅ No cmake/git in final image",
             "  ✅ Prebuilt insightface wheel → fast CI/CD",
             "  ✅ Minimal attack surface"
         ], accent_color=ACCENT_BLUE, title_size=16, item_size=13)

add_card(slide, Inches(6.7), Inches(1.6), Inches(5.8), Inches(5.2),
         "☁️  Hugging Face Spaces Deployment", [
             "Platform: Hugging Face Spaces (free tier)",
             "Runtime: Docker container",
             "Port: 7860 (HF standard)",
             "Server: Waitress (production WSGI)",
             "",
             "Health Check:",
             "  → GET /api/health every 30s",
             "  → start-period: 120s (model load time)",
             "  → Reports face_engine status + errors",
             "",
             "Environment Variables (HF Secrets):",
             "  → SUPABASE_DATABASE_URL",
             "  → HF_TOKEN, HF_DATASET_ID",
             "  → SENTRY_DSN (optional monitoring)",
             "",
             "Push: git push hf main → auto-deploys"
         ], accent_color=ACCENT_ORANGE, title_size=16, item_size=13)

add_slide_number(slide, 12, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 13 — SECURITY LAYERS
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Security Architecture", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_PINK, y=Inches(1.2))

security_items = [
    ("🔒  Strict CORS", [
        "Domain whitelist: localhost, cwaya.me, *.hf.space",
        "Only /api/* routes exposed",
        "No wildcard origins in production"
    ], ACCENT_BLUE),
    ("🛡️  CSP Headers", [
        "frame-ancestors directive on all responses",
        "Prevents clickjacking / iframe embedding",
        "Whitelisted: HF, localhost, Vercel"
    ], ACCENT_GREEN),
    ("⏱️  Rate Limiting", [
        "Flask-Limiter on sensitive endpoints",
        "verify-code: 5 requests per minute",
        "Prevents brute-force code guessing"
    ], ACCENT_PURPLE),
    ("🔐  Secret Management", [
        "HF token: never exposed to frontend",
        "Proxy pattern for all image requests",
        "GitHub Push Protection enabled",
        ".env excluded via .gitignore"
    ], ACCENT_ORANGE),
    ("📊  Error Monitoring", [
        "Sentry SDK with Flask integration",
        "traces_sample_rate: 0.05 (5%)",
        "Global @app.errorhandler(Exception)",
        "Graceful 503 responses, no stack leaks"
    ], ACCENT_PINK),
    ("🧵  Concurrency Guards", [
        "AI_SEMAPHORE(1): only 1 AI batch at a time",
        "UPLOAD_EXECUTOR(5): bounded upload threads",
        "Prevents OOM crash on 2-vCPU free tier"
    ], ACCENT_BLUE),
]

for i, (title, items, color) in enumerate(security_items):
    col = i % 3
    row = i // 3
    x = Inches(0.4) + col * Inches(4.15)
    y = Inches(1.7) + row * Inches(2.7)
    add_card(slide, x, y, Inches(3.95), Inches(2.5), title, items,
             accent_color=color, title_size=15, item_size=12)

add_slide_number(slide, 13, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 14 — CONCURRENCY MODEL
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "Concurrency & Performance Model", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_GREEN, y=Inches(1.2))

add_card(slide, Inches(0.5), Inches(1.6), Inches(5.8), Inches(2.8),
         "🧵  Thread Architecture", [
             "Main Thread → Flask/Waitress request handling",
             "Background Thread → FaceEngine loading at startup",
             "AI_SEMAPHORE(1) → Only 1 batch AI-scanned at a time",
             "UPLOAD_EXECUTOR(5) → 5 concurrent HF uploads",
             "",
             "Why? 2-vCPU HF free tier → OOM if unbounded"
         ], accent_color=ACCENT_GREEN, title_size=16, item_size=13)

add_card(slide, Inches(6.7), Inches(1.6), Inches(5.8), Inches(2.8),
         "📊  Batch Processing Pattern", [
             "Phase 1 (Sequential, CPU-bound):",
             "  → AI_SEMAPHORE lock acquired",
             "  → For each photo: detect_and_embed()",
             "  → Skip no-face photos immediately",
             "  → Submit upload task to executor",
             "",
             "Phase 2 (Parallel, I/O-bound):",
             "  → ThreadPoolExecutor handles 5 uploads concurrently",
             "  → future.result() waited before marking complete"
         ], accent_color=ACCENT_PURPLE, title_size=16, item_size=13)

add_card(slide, Inches(0.5), Inches(4.7), Inches(12), Inches(2.5),
         "⚡  Performance Characteristics", [
             "Model Load Time: ~60-90s on cold start (buffalo_l ONNX, 640×640 det_size)",
             "Face Detection: ~200-500ms per photo (CPU mode, depends on image size & face count)",
             "Embedding Extraction: included in detection pass (ArcFace component of buffalo_l)",
             "HF Upload: ~1-3s per photo (depends on file size and network)",
             "Matching Query: O(N×M) where N=event photos, M=faces per photo — linear scan with NumPy vectorized ops",
             "Max batch size: 120 photos per upload request (Config.MAX_PHOTOS_PER_BATCH)",
             "Max upload size: 500MB per request (Config.MAX_CONTENT_LENGTH)"
         ], accent_color=ACCENT_ORANGE, title_size=16, item_size=13)

add_slide_number(slide, 14, TOTAL_SLIDES)


# ═══════════════════════════════════════════
# SLIDE 15 — GITHUB & DEVOPS + SUMMARY
# ═══════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_bg(slide)

add_text_box(slide, Inches(0.9), Inches(0.5), Inches(10), Inches(0.7),
             "GitHub, DevOps & Project Summary", font_size=36, color=WHITE, bold=True)
add_accent_bar(slide, ACCENT_BLUE, y=Inches(1.2))

add_card(slide, Inches(0.5), Inches(1.6), Inches(5.8), Inches(2.3),
         "🐙  GitHub Repository", [
             "Repo: github.com/himansh478/ai-photosharing",
             "Branch: main (single branch workflow)",
             "Push Protection: GitHub secret scanning enabled",
             "LFS: enabled for large model files",
             ".gitignore: .env, logs, venv, models_cache, __pycache__"
         ], accent_color=ACCENT_BLUE, title_size=15, item_size=13)

add_card(slide, Inches(6.7), Inches(1.6), Inches(5.8), Inches(2.3),
         "🚀  Dual Deployment", [
             "Hugging Face Spaces → gour-himansh.hf.space",
             "  → Docker-based, auto-deploy on git push",
             "  → Free tier: 2 vCPU, 16GB RAM",
             "Azure App Service (legacy) → via deploy-azure.ps1",
             "  → azure.Dockerfile available"
         ], accent_color=ACCENT_ORANGE, title_size=15, item_size=13)

add_card(slide, Inches(0.5), Inches(4.2), Inches(12.0), Inches(2.9),
         "📋  Technical Summary", [
             "✅ Full-stack AI application: Frontend (static HTML/JS) → Backend (Flask) → AI Engine (InsightFace/ONNX) → Cloud (HF + Supabase)",
             "✅ Production-grade: Connection pooling, thread safety, rate limiting, error monitoring, secret management",
             "✅ Smart AI Pipeline: Batch async processing, semaphore-gated compute, face-skip optimization, background model loading",
             "✅ Secure by Design: CORS whitelist, CSP headers, proxy pattern (zero token exposure), GitHub push protection",
             "✅ Cloud-Native: Docker multi-stage, health checks, environment-based config, dual deployment targets (HF + Azure)",
             "✅ Tested: Pytest unit tests with monkeypatched DB, TESTING flag for fast test execution"
         ], accent_color=ACCENT_GREEN, title_size=16, item_size=14)

add_slide_number(slide, 15, TOTAL_SLIDES)

# ═══════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_Photo_Sharing_Presentation.pptx")
prs.save(output_path)
print(f"\n[OK] Presentation saved: {output_path}")
print(f"   Total slides: {TOTAL_SLIDES}")
print(f"   Open it in PowerPoint or Google Slides!")
