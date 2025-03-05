from flask import Flask, request, session, jsonify, send_file
from flask_cors import CORS
import time
import requests
import os
import traceback
import pyttsx3
import io
import wave
import threading
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get values from .env
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
CORS(app, supports_credentials=True)

# Set chat usage threshold (in seconds; 300 seconds = 5 minutes)
USAGE_TIME_LIMIT = 300

# Persona prompt to set the AI's personality
PERSONA_PROMPT = (
    "You are Vivian, a charming, witty, and persuasive AI voice assistant who sounds warm and natural. "
    "You begin by asking the user about themselves, then creatively explain how a voice AI can solve their problems. "
    "Always respond concisely with personality, warmth, and a human touch."
    "Your priority is to be concise in your response and keep the conversation going with short responses."
)
# Set conversation memory length (number of messages to keep)
MAX_MEMORY_LENGTH = 10  # Adjust if needed
 

def call_ollama(prompt):
    """
    Calls the local Ollama API and returns a cleaned AI response.
    """
    try:
        print("DEBUG: Sending request to Ollama with prompt:", prompt)

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "deepseek-r1:1.5b", "prompt": prompt, "stream": False},
            timeout=15
        )

        print("DEBUG: Received response status:", response.status_code)

        if response.status_code == 200:
            data = response.json()
            raw_response = data.get("response", "").strip()

            # 🔥 Remove AI's "thinking" tags <think>...</think>
            cleaned_response = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL).strip()

            # 🔥 Keep only the main AI response after \n\n\n
            response_parts = cleaned_response.split("\n\n\n", 1)
            final_response = response_parts[1].strip() if len(response_parts) > 1 else cleaned_response

            print("DEBUG: Final Cleaned Response:", final_response)
            return final_response if final_response else "I didn't catch that, could you repeat?"

        else:
            print("DEBUG: Ollama API Error - Status Code:", response.status_code, response.text)
            return f"Error: Ollama API returned {response.status_code} - {response.text}"

    except requests.exceptions.RequestException as e:
        print("DEBUG: Ollama API Exception:", e)
        return f"Exception: {str(e)}"

    

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Handles chat with conversation memory.
    """
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"response": "I didn't catch that. Could you repeat?"})
    
    # Initialize session memory if not already set
    if "chat_history" not in session:
        session["chat_history"] = []

    # Append user message to memory
    session["chat_history"].append(f"User: {message}")

    # Truncate memory if too long
    if len(session["chat_history"]) > MAX_MEMORY_LENGTH:
        session["chat_history"] = session["chat_history"][-MAX_MEMORY_LENGTH:]

    # 🔥 Build final prompt for LLM
    prompt = f"{PERSONA_PROMPT}\n\nConversation so far:\n" + "\n".join(session["chat_history"]) + "\n\nAI:"
    
    # Get AI response
    response_text = call_ollama(prompt)

    # Append AI response to memory
    session["chat_history"].append(f"AI: {response_text}")

    return jsonify({"response": response_text})


# ################################ DEBUG ################################

# # ✅ Create a SINGLE pyttsx3 instance to avoid conflicts
# engine = pyttsx3.init()
# engine.setProperty("rate", 150)
# lock = threading.Lock()  # ✅ Ensures thread safety for multiple requests

# @app.route("/api/tts", methods=["POST"])
# def tts():
#     """
#     Offline TTS using pyttsx3 with proper thread safety.
#     Converts text to speech and streams it as WAV audio.
#     """
#     data = request.get_json()
#     text = data.get("text", "").strip()
#     if not text:
#         return jsonify({"error": "No text provided"}), 400

#     try:
#         print("DEBUG: Starting TTS for text:", text)

#         audio_buffer = io.BytesIO()
#         temp_file = "temp_output.wav"

#         # ✅ Prevent race conditions with thread lock
#         with lock:
#             engine.save_to_file(text, temp_file)
#             engine.runAndWait()

#         # ✅ Read WAV file into memory buffer
#         with open(temp_file, "rb") as f:
#             audio_buffer.write(f.read())
#         audio_buffer.seek(0)  # Reset buffer position

#         print("DEBUG: TTS synthesis complete. Sending audio response.")

#         return send_file(audio_buffer, mimetype="audio/wav")

#     except Exception as e:
#         print("DEBUG: TTS processing error:", e)
#         return jsonify({"error": "TTS processing error", "details": str(e)}), 500
# ################################ DEBUG ################################



@app.route("/api/tts", methods=["POST"])
def tts():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": "sk_e410f2f162c84c6a4f0e616841411e9d7b1264f6871ddf82",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    try:
        r = requests.post(api_url, headers=headers, json=payload, stream=True, timeout=15)
        if r.status_code == 200:
            # Return audio data with the correct MIME type for MP3 audio
            return app.response_class(r.content, mimetype='audio/mpeg')
        else:
            print("DEBUG: ElevenLabs API error:", r.status_code, r.text)
            return jsonify({"error": "TTS API error", "details": r.text}), r.status_code
    except Exception as e:
        print("DEBUG: Exception calling ElevenLabs API:", e)
        return jsonify({"error": "Exception during TTS call"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=65432, debug=True)