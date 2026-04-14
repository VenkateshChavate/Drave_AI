from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from pymongo import MongoClient
from datetime import datetime
import os

# =========================
# APP SETUP
# =========================
app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
MODEL = "gemini-3-flash-preview"  # Model name for Gemini
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# CONFIGURE THE CORRECT API KEY
# =========================
API_KEY = "AIzaSyD5poditKspIEsxvLpmz5H3IPaDSFX2xHI"  # Updated API Key
client = genai.Client(api_key=API_KEY)  # Initialize Gemini API client with the updated API key

# =========================
# MONGODB
# =========================
try:
    client_db = MongoClient("mongodb://127.0.0.1:27017/")  # MongoDB connection
    db = client_db["drave"]
    collection = db["messages"]
    print("MongoDB Connected ✅")
except Exception as e:
    print("MongoDB Error:", e)

# =========================
# HOME ROUTE
# =========================
@app.route("/")
def home():
    return "Drave Backend Running ✅"

# =========================
# CHAT API ROUTE
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    user_message = data.get("message", "").strip()
    chat_id = data.get("chatId", "default")
    history = data.get("history", [])

    if not user_message:
        return jsonify({"reply": "⚠️ Empty message"})

    # 🔥 Build context
    context = ""
    for msg in history[-5:]:  # Include only the last 5 messages for context
        role = "User" if msg["role"] == "user" else "Assistant"
        context += f"{role}: {msg['text']}\n"

    prompt = f"""
You are a friendly and knowledgeable AI assistant.

Guidelines:
- Provide direct, clear answers with examples if necessary.
- Offer coding solutions, explanations, or general advice.
- Always admit when you're unsure of something.

Context of Conversation:
{context}
User's Question: {user_message}
AI Response:
"""
    try:
        # Use the Gemini API to generate content based on the prompt
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        reply = response.text.strip()  # Extract the response text from Gemini API

        if not reply:
            reply = "⚠️ Empty response from model"

        # ✅ SAVE USER MESSAGE in MongoDB
        collection.insert_one({
            "chatId": chat_id,
            "role": "user",
            "text": user_message,
            "createdAt": datetime.utcnow()
        })

        # ✅ SAVE AI RESPONSE in MongoDB
        collection.insert_one({
            "chatId": chat_id,
            "role": "ai",
            "text": reply,
            "createdAt": datetime.utcnow()
        })

    except Exception as e:
        reply = f"❌ Server error: {str(e)}"

    return jsonify({"reply": reply})

# =========================
# HISTORY API ROUTE
# =========================
@app.route("/history/<chat_id>", methods=["GET"])
def history(chat_id):
    try:
        # Fetch chat history from MongoDB based on the provided chat_id
        chats = list(collection.find(
            {"chatId": chat_id},
            {"_id": 0}
        ).sort("createdAt", 1))  # Sort by creation date in ascending order

        return jsonify(chats)

    except Exception as e:
        return jsonify({"error": str(e)})

# =========================
# FILE UPLOAD API ROUTE
# =========================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files.get("file")
        chat_id = request.form.get("chatId", "default")

        if not file:
            return jsonify({"reply": "No file received"})

        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # ✅ SAVE FILE UPLOAD INFO in DB
        collection.insert_one({
            "chatId": chat_id,
            "role": "user",
            "text": f"📎 Uploaded: {filename}",
            "file": filepath,
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
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)