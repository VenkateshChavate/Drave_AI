const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");

const app = express();

/* ✅ MIDDLEWARE */
app.use(cors());
app.use(express.json());

/* ✅ CONNECT MONGODB */
mongoose.connect("mongodb://127.0.0.1:27017/drave")
.then(() => console.log("MongoDB Connected ✅"))
.catch(err => console.log("Mongo Error ❌", err));

/* ✅ SCHEMA */
const ChatSchema = new mongoose.Schema({
  chatId: String,
  role: String,
  text: String,
  createdAt: { type: Date, default: Date.now }
});

const Chat = mongoose.model("Chat", ChatSchema);

/* ✅ TEST ROUTE */
app.get("/", (req,res)=>{
  res.send("Server running ✅");
});

/* ✅ CHAT API */
app.post("/chat", async (req, res) => {
  try {
    console.log("BODY:", req.body);

    const { message, chatId } = req.body;

    if (!message || !chatId) {
      return res.json({ reply: "Missing message/chatId ❌" });
    }

    /* ✅ SAVE USER */
    await Chat.create({
      chatId,
      role: "user",
      text: message
    });

    console.log("User saved ✅");

    /* 🤖 SIMPLE REPLY (TEST) */
    const reply = "Reply: " + message;

    /* ✅ SAVE AI */
    await Chat.create({
      chatId,
      role: "ai",
      text: reply
    });

    console.log("AI saved ✅");

    res.json({ reply });

  } catch (err) {
    console.error("ERROR:", err);
    res.status(500).json({ reply: "Server error ❌" });
  }
});

/* ✅ HISTORY */
app.get("/history/:id", async (req, res) => {
  try {
    const data = await Chat.find({ chatId: req.params.id })
      .sort({ createdAt: 1 });

    res.json(data);
  } catch (err) {
    res.status(500).json({ error: "Fetch error" });
  }
});

/* ✅ START SERVER */
app.listen(5000, () => {
  console.log("Server running → http://127.0.0.1:5000 🚀");
});