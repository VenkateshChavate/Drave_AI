from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import io
from google import genai
from google.genai import types
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import uuid
import bcrypt
import jwt
from functools import wraps
from fpdf import FPDF
import re

# =========================
# APP SETUP
# =========================
app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
MODEL              = "gemini-2.5-flash"
IMAGE_MODEL        = "gemini-2.0-flash-exp-image-generation"
UPLOAD_FOLDER      = "uploads"
GENERATED_FOLDER   = "generated"
JWT_SECRET         = "drave_secret_key_change_in_production"   # ⚠️ change this in prod
JWT_EXPIRY_DAYS    = 7

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# =========================
# GEMINI CLIENT
# =========================
API_KEY = ""
client  = genai.Client(api_key=API_KEY)

# =========================
# MONGODB
# =========================
try:
    client_db  = MongoClient("mongodb://127.0.0.1:27017/")
    db         = client_db["drave"]
    collection = db["messages"]
    users_col  = db["users"]
    users_col.create_index("email", unique=True)
    print("MongoDB Connected ✅")
except Exception as e:
    print("MongoDB Error:", e)

# =========================
# AUTH DECORATOR
# =========================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user_id = data['userId']
        except Exception:
            return jsonify({"error": "Token is invalid"}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

# =========================
# HOME ROUTE
# =========================
@app.route("/")
def home():
    return "Drave Backend Running ✅"

# =========================
# AUTH — REGISTER
# =========================
@app.route("/auth/register", methods=["POST"])
def register():
    try:
        data     = request.get_json()
        name     = data.get("name", "").strip()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not name or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        if users_col.find_one({"email": email}):
            return jsonify({"error": "Email already registered"}), 409

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        user_id = str(uuid.uuid4())
        users_col.insert_one({
            "_id":        user_id,
            "name":       name,
            "email":      email,
            "password":   hashed,
            "createdAt":  datetime.utcnow()
        })

        token = jwt.encode(
            {
                "userId": user_id,
                "email":  email,
                "exp":    datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS)
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        return jsonify({
            "token": token,
            "user":  {"id": user_id, "name": name, "email": email}
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# AUTH — LOGIN
# =========================
@app.route("/auth/login", methods=["POST"])
def login():
    try:
        data     = request.get_json()
        email    = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user = users_col.find_one({"email": email})
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            return jsonify({"error": "Invalid email or password"}), 401

        token = jwt.encode(
            {
                "userId": str(user["_id"]),
                "email":  email,
                "exp":    datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS)
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        return jsonify({
            "token": token,
            "user":  {
                "id":    str(user["_id"]),
                "name":  user["name"],
                "email": user["email"]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# AUTH — FORGOT PASSWORD
# =========================
@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        if not email:
            return jsonify({"error": "Email is required"}), 400

        user = users_col.find_one({"email": email})
        if not user:
            # For security, we don't confirm if the account exists
            return jsonify({"message": "If an account exists, a reset link will be sent"}), 200

        # Create a short-lived token (15 mins)
        token = jwt.encode(
            {
                "userId": str(user["_id"]),
                "exp":    datetime.utcnow() + timedelta(minutes=15)
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        # In a real app, send an email. For simulation, we return it to the UI.
        return jsonify({
            "message": "Reset link generated (Simulated)",
            "resetToken": token
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# AUTH — RESET PASSWORD
# =========================
@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        token = data.get("token")
        password = data.get("password")

        if not token or not password:
            return jsonify({"error": "Missing token or password"}), 400

        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["userId"]

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        users_col.update_one({"_id": user_id}, {"$set": {"password": hashed}})

        return jsonify({"message": "Password updated successfully"}), 200

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"error": "Invalid or expired reset link"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# CHAT API ROUTE
# =========================
@app.route("/chat", methods=["POST"])
@token_required
def chat(current_user_id):
    data = request.get_json()

    user_message = data.get("message", "").strip()
    chat_id      = data.get("chatId", "default")

    if not user_message:
        return jsonify({"reply": "⚠️ Empty message"})

    context = ""
    history = list(collection.find(
        {"chatId": chat_id, "userId": current_user_id},
        {"_id": 0}
    ).sort("createdAt", -1).limit(5))
    history.reverse()

    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        text = msg["text"]

        if "file" in msg and os.path.exists(msg["file"]):
            try:
                with open(msg["file"], "r", encoding="utf-8") as f:
                    file_data = f.read()
                    text += f"\n[Document Content of {os.path.basename(msg['file'])}]:\n{file_data[:3000]}"
            except Exception:
                pass

        context += f"{role}: {text}\n"

    prompt = (
        "You are Drave, a friendly and knowledgeable AI assistant.\n\n"
        "Guidelines:\n"
        "- Provide direct, clear, well-structured answers.\n"
        "- Do NOT use markdown formatting by default. Use plain text for normal responses.\n"
        "- If the user explicitly asks for a table, tabular format, comparison, or differences, output a proper Markdown table using | column separators and a header separator line (e.g., |---|---|).\n"
        "- Use plain numbered lists (1. 2. 3.) or lettered lists if needed.\n"
        "- Separate sections with a blank line for readability.\n"
        "- For code, just write the code block plainly without triple backtick fencing.\n"
        "- Always admit when you are unsure of something.\n\n"
        f"Conversation History:\n{context}"
        f"User: {user_message}\nDrave:"
    )

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        reply    = response.text.strip()

        if not reply:
            reply = "⚠️ Empty response from model"

        collection.insert_one({
            "chatId":    chat_id,
            "role":      "user",
            "text":      user_message,
            "userId":    current_user_id,
            "createdAt": datetime.utcnow()
        })
        collection.insert_one({
            "chatId":    chat_id,
            "role":      "ai",
            "text":      reply,
            "userId":    current_user_id,
            "createdAt": datetime.utcnow()
        })

    except Exception as e:
        reply = f"❌ Server error: {str(e)}"

    return jsonify({"reply": reply})

# =========================
# GET ALL USER CHATS
# =========================
@app.route("/chats", methods=["GET"])
@token_required
def get_user_chats(current_user_id):
    try:
        chat_ids = collection.distinct("chatId", {"userId": current_user_id})
        return jsonify(chat_ids)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# HISTORY API ROUTE
# =========================
@app.route("/history/<chat_id>", methods=["GET"])
@token_required
def history(current_user_id, chat_id):
    try:
        chats = list(collection.find(
            {"chatId": chat_id, "userId": current_user_id},
            {"_id": 0}
        ).sort("createdAt", 1))
        return jsonify(chats)
    except Exception as e:
        return jsonify({"error": str(e)})

# =========================
# FILE UPLOAD API ROUTE
# =========================
@app.route("/upload", methods=["POST"])
@token_required
def upload(current_user_id):
    try:
        file    = request.files.get("file")
        chat_id = request.form.get("chatId", "default")

        if not file:
            return jsonify({"reply": "No file received"})

        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        reply = ""
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".txt", ".md", ".py", ".js", ".html", ".css", ".csv", ".json"]:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    file_text = f.read()

                prompt = (
                    f"The user has uploaded a file named '{filename}'.\n\n"
                    f"Content:\n{file_text[:8000]}\n\n"
                    "Please analyze this file and provide a helpful summary. "
                    "Do NOT use markdown. Keep it plain text."
                )
                response = client.models.generate_content(model=MODEL, contents=prompt)
                reply = response.text.strip()
            except Exception as e:
                reply = f"File {filename} uploaded, but analysis failed: {str(e)}"

        if not reply:
            reply = f"File {filename} uploaded successfully. (Analysis is available for text-based files)."

        collection.insert_one({
            "chatId":    chat_id,
            "role":      "user",
            "text":      f"📎 Uploaded: {filename}",
            "file":      filepath,
            "userId":    current_user_id,
            "createdAt": datetime.utcnow()
        })

        collection.insert_one({
            "chatId":    chat_id,
            "role":      "ai",
            "text":      reply,
            "userId":    current_user_id,
            "createdAt": datetime.utcnow()
        })

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"❌ Error: {str(e)}"})

# =========================
# SERVE UPLOADED FILES
# =========================
@app.route("/uploads/<filename>")
def get_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# =========================
# IMAGE GENERATION ROUTE
# =========================
@app.route("/generate-image", methods=["POST"])
@token_required
def generate_image(current_user_id):
    try:
        data   = request.get_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            )
        )

        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                break

        if not image_data:
            return jsonify({"error": "No image was generated"}), 500

        filename  = f"{uuid.uuid4().hex}.png"
        filepath  = os.path.join(GENERATED_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        chat_id = data.get("chatId", "default")
        collection.insert_one({
            "chatId":    chat_id,
            "role":      "ai",
            "type":      "image",
            "imageUrl":  f"/generated/{filename}",
            "text":      f"🖼️ Generated: {prompt}",
            "userId":    current_user_id,
            "createdAt": datetime.utcnow()
        })

        return jsonify({"imageUrl": f"/generated/{filename}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# SERVE GENERATED IMAGES
# =========================
@app.route("/generated/<filename>")
def get_generated_image(filename):
    return send_from_directory(GENERATED_FOLDER, filename)

# =========================
# PDF GENERATION  —  Modern Redesign
# =========================
class DravePDF(FPDF):
    """Premium PDF formatter for Drave AI responses."""

    # ── Design Tokens ────────────────────────────────────
    COL_BG       = (250, 250, 250)      # #fafafa  page bg
    COL_HEADER   = (26,  23,  23)       # #1a1717  dark header
    COL_ACCENT   = (230, 57,  70)       # #e63946  Drave red
    COL_ACCENT_D = (193, 18,  31)       # #c1121f  deep red
    COL_TEXT     = (32,  32,  32)       # #202020  body text
    COL_TEXT_M   = (80,  80,  80)       # #505050  secondary text
    COL_TEXT_L   = (120, 120, 120)      # #787878  muted text
    COL_CODE_BG  = (244, 244, 245)      # #f4f4f5  code background
    COL_RULE     = (230, 230, 230)      # #e6e6e6  horizontal rule

    MARGIN_L     = 20
    MARGIN_R     = 20
    MARGIN_T     = 18
    CONTENT_W    = 210 - MARGIN_L - MARGIN_R   # ~170 mm

    def __init__(self, title="Drave Response"):
        super().__init__(unit="mm", format="A4")
        self.title = title
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(self.MARGIN_L, self.MARGIN_T, self.MARGIN_R)
        self.add_page()
        self._draw_page_background()

    # ── Helpers ──────────────────────────────────────────
    def _set_fill(self, rgb):
        self.set_fill_color(*rgb)

    def _set_draw(self, rgb):
        self.set_draw_color(*rgb)

    def _set_text(self, rgb):
        self.set_text_color(*rgb)

    def _draw_page_background(self):
        """Fill entire page with light background color."""
        self._set_fill(self.COL_BG)
        self.rect(0, 0, 210, 297, style="F")

    # ── Header ───────────────────────────────────────────
    def header(self):
        # Dark brand bar spanning full width
        self._set_fill(self.COL_HEADER)
        self.rect(0, 0, 210, 28, style="F")

        # Red accent dot
        self._set_fill(self.COL_ACCENT)
        self.ellipse(self.MARGIN_L, 11, 5, 5, style="F")

        # "Drave" wordmark
        self.set_xy(self.MARGIN_L + 8, 9)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "Drave", ln=False)

        # Subtitle
        self.set_xy(self.MARGIN_L + 8, 17)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 5, "AI Expert", ln=False)

        # Generation timestamp (right-aligned)
        ts = datetime.now().strftime("%b %d, %Y  ·  %H:%M")
        self.set_xy(0, 11)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(140, 140, 140)
        self.cell(210 - self.MARGIN_R, 5, ts, align="R")

        # Thin red underline below header
        self._set_draw(self.COL_ACCENT)
        self.set_line_width(0.6)
        self.line(self.MARGIN_L, 28, 210 - self.MARGIN_R, 28)
        self.set_line_width(0.2)
        self.ln(32)

    # ── Footer ───────────────────────────────────────────
    def footer(self):
        y = -22
        # Separator line
        self._set_draw(self.COL_RULE)
        self.set_line_width(0.3)
        self.line(self.MARGIN_L, 297 + y + 4, 210 - self.MARGIN_R, 297 + y + 4)

        # Red accent line above footer text
        self._set_draw(self.COL_ACCENT)
        self.set_line_width(0.8)
        self.line(self.MARGIN_L, 297 + y + 6, 210 - self.MARGIN_R, 297 + y + 6)
        self.set_line_width(0.2)

        self.set_y(297 + y + 9)
        self.set_font("Helvetica", "", 8)
        self._set_text(self.COL_TEXT_L)
        self.cell(
            0, 5,
            f"Generated by Drave    ·    {datetime.now().strftime('%Y-%m-%d %H:%M')}    ·    Page {self.page_no()}",
            align="C"
        )

    # ── Content Rendering ────────────────────────────────
    def add_response(self, text, prompt=None):
        # Red vertical accent bar on the left
        self._set_fill(self.COL_ACCENT)
        self.rect(self.MARGIN_L - 5, self.get_y(), 2.5, 12, style="F")

        self.set_x(self.MARGIN_L)
        self.set_font("Helvetica", "B", 15)
        self._set_text(self.COL_TEXT)

        title = self._safe_text(prompt if prompt else "Response")
        self.multi_cell(self.CONTENT_W, 8, title)
        self.ln(3)

        # Clean text: strip markdown artifacts
        cleaned = self._clean_markdown(text)
        paragraphs = cleaned.split("\n")

        for raw in paragraphs:
            para = raw.rstrip()
            if not para:
                self.ln(3)
                continue

            stripped = para.lstrip()

            # ── Code block detection ──
            if self._is_code_line(stripped):
                self._render_code_block(stripped)
                continue

            # ── Heading detection ──
            if self._is_heading(stripped):
                self._render_heading(stripped)
                continue

            # ── Numbered list ──
            if self._is_numbered_list(stripped):
                self._render_numbered_item(stripped)
                continue

            # ── Bullet list ──
            if self._is_bullet_list(stripped):
                self._render_bullet_item(stripped)
                continue

            # ── Horizontal rule ──
            if stripped.replace("-", "").replace("=", "").replace("*", "") == "" and len(stripped) >= 3:
                self._render_horizontal_rule()
                continue

            # ── Regular paragraph ──
            self.set_x(self.MARGIN_L)
            self.set_font("Helvetica", "", 11)
            self._set_text(self.COL_TEXT)
            self.multi_cell(self.CONTENT_W, 6, self._safe_text(stripped))
            self.ln(2)

    def _safe_text(self, text):
        """Sanitize text for Latin-1 core fonts like Helvetica."""
        if not text: return ""
        # Replace common Unicode symbols used by LLMs with Latin-1 equivalents
        replacements = {
            "\u2022": "-", # Bullet point
            "\u2013": "-", # en dash
            "\u2014": "-", # em dash
            "\u201c": '"', # left double quote
            "\u201d": '"', # right double quote
            "\u2018": "'", # left single quote
            "\u2019": "'", # right single quote
            "\u2122": "TM",
            "\u00ae": "(R)",
            "\u00a9": "(C)",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Encode to latin-1 and ignore any remaining unsupported characters (like emojis)
        return text.encode("latin-1", "ignore").decode("latin-1")

    # ── Markdown Cleaning ────────────────────────────────
    def _clean_markdown(self, text):
        """Remove common markdown formatting artifacts."""
        t = text.replace("\r", "")
        t = re.sub(r"```\w*\n?", "", t)
        t = re.sub(r"```", "", t)
        t = re.sub(r"`([^`]+)`", r"\1", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"\*([^*]+)\*", r"\1", t)
        t = re.sub(r"__([^_]+)__", r"\1", t)
        t = re.sub(r"_([^_]+)_", r"\1", t)
        t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
        return t

    # ── Line Type Detection ──────────────────────────────
    def _is_code_line(self, stripped):
        return (stripped.startswith("    ") or
                stripped.startswith("\t") or
                (len(stripped) > 2 and stripped[:2] in ("  ", " \t")))

    def _is_heading(self, stripped):
        return stripped.endswith(":") and len(stripped) < 80 and not stripped[:-1].endswith(".")

    def _is_numbered_list(self, stripped):
        return bool(re.match(r"^\d+\.\s", stripped))

    def _is_bullet_list(self, stripped):
        return stripped.startswith(("- ", "• ", "* ", "+ "))

    # ── Element Renderers ────────────────────────────────
    def _render_code_block(self, text):
        code = text.lstrip().lstrip("\t")
        x = self.MARGIN_L + 4
        y = self.get_y()

        self.set_font("Courier", "", 9.5)
        self._set_text(self.COL_TEXT_M)
        safe_code = self._safe_text(code)
        lines_needed = self.get_string_width(safe_code) / (self.CONTENT_W - 12)
        height = max(6, (int(lines_needed) + 1) * 4.5)

        self._set_fill(self.COL_CODE_BG)
        self._set_draw(self.COL_RULE)
        self.rect(x - 2, y - 1, self.CONTENT_W - 8, height + 2, style="FD")

        self.set_xy(x, y + 0.8)
        self.multi_cell(self.CONTENT_W - 12, 4.5, safe_code)
        self.ln(3)

    def _render_heading(self, text):
        self.set_x(self.MARGIN_L)
        self.set_font("Helvetica", "B", 12.5)
        self._set_text(self.COL_TEXT)
        self.multi_cell(self.CONTENT_W, 7, self._safe_text(text))
        self._set_draw(self.COL_ACCENT)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(self.MARGIN_L, y + 1, self.MARGIN_L + 25, y + 1)
        self.set_line_width(0.2)
        self.ln(4)

    def _render_numbered_item(self, text):
        match = re.match(r"^(\d+\.)\s+(.*)", text)
        if not match:
            return
        num, body = match.groups()

        self.set_x(self.MARGIN_L)
        self.set_font("Helvetica", "B", 11)
        self._set_text(self.COL_ACCENT_D)
        self.cell(8, 6, num, ln=False)

        self.set_font("Helvetica", "", 11)
        self._set_text(self.COL_TEXT)
        self.multi_cell(self.CONTENT_W - 10, 6, self._safe_text(body))
        self.ln(1.5)

    def _render_bullet_item(self, text):
        body = text[2:]

        self.set_x(self.MARGIN_L + 2)
        self.set_font("Helvetica", "B", 11)
        self._set_text(self.COL_ACCENT)
        self.cell(5, 6, "-", ln=False)

        self.set_font("Helvetica", "", 11)
        self._set_text(self.COL_TEXT)
        self.multi_cell(self.CONTENT_W - 10, 6, self._safe_text(body))
        self.ln(1.5)

    def _render_horizontal_rule(self):
        self.ln(2)
        self._set_draw(self.COL_RULE)
        self.set_line_width(0.3)
        y = self.get_y()
        self.line(self.MARGIN_L + 20, y, 210 - self.MARGIN_R - 20, y)
        self.set_line_width(0.2)
        self.ln(4)


@app.route("/download-pdf", methods=["POST"])
@token_required
def download_pdf(current_user_id):
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        prompt = data.get("prompt", "").strip()

        if not text:
            return jsonify({"error": "No text provided"}), 400

        pdf = DravePDF()
        pdf.add_response(text, prompt=prompt)

        filename = f"drave-response-{uuid.uuid4().hex[:8]}.pdf"
        pdf_buffer = io.BytesIO()
        pdf.output(pdf_buffer)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
