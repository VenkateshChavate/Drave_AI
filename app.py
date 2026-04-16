from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import uuid
import bcrypt
import jwt
from functools import wraps

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
API_KEY = "key"
client  = genai.Client(api_key=API_KEY)

# =========================
# MONGODB
# =========================
try:
    client_db  = MongoClient("mongodb://127.0.0.1:27017/")
    db         = client_db["drave"]
    collection = db["messages"]
    users_col  = db["users"]           # ← new collection for auth
    users_col.create_index("email", unique=True)   # prevent duplicate emails
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

        # ── Validation ──────────────────────────────────
        if not name or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        # ── Check if email already exists ───────────────
        if users_col.find_one({"email": email}):
            return jsonify({"error": "Email already registered"}), 409

        # ── Hash password ────────────────────────────────
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # ── Save user ────────────────────────────────────
        user_id = str(uuid.uuid4())
        users_col.insert_one({
            "_id":        user_id,
            "name":       name,
            "email":      email,
            "password":   hashed,
            "createdAt":  datetime.utcnow()
        })

        # ── Generate JWT ─────────────────────────────────
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

        # ── Validation ──────────────────────────────────
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # ── Find user ────────────────────────────────────
        user = users_col.find_one({"email": email})
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        # ── Check password ───────────────────────────────
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            return jsonify({"error": "Invalid email or password"}), 401

        # ── Generate JWT ─────────────────────────────────
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

    # Securely build context from DB (do not trust history sent by client)
    context = ""
    history = list(collection.find(
        {"chatId": chat_id, "userId": current_user_id},
        {"_id": 0}
    ).sort("createdAt", -1).limit(5))
    history.reverse()

    for msg in history[-5:]:
        role     = "User" if msg["role"] == "user" else "Assistant"
        context += f"{role}: {msg['text']}\n"

    prompt = (
        "You are Drave, a friendly and knowledgeable AI assistant.\n\n"
        "Guidelines:\n"
        "- Provide direct, clear, well-structured answers.\n"
        "- Do NOT use any markdown formatting.\n"
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

        collection.insert_one({
            "chatId":    chat_id,
            "role":      "user",
            "text":      f"📎 Uploaded: {filename}",
            "file":      filepath,
            "userId":    current_user_id,
            "createdAt": datetime.utcnow()
        })

        return jsonify({"reply": f"File {filename} uploaded successfully"})

    except Exception as e:
        return jsonify({"reply": str(e)})

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

        # Save record to DB for history tracking
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
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)