# strlt_app.py - updated
import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import streamlit.components.v1 as components
import re
import time
import numpy as np
import uuid
import urllib.parse
import os
import groq
from groq import Groq
import tempfile

# Page config
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬")

# ---- Init Groq client once per session ----
@st.cache_resource
def init_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        st.error("🤖 Falta GROQ_API_KEY!")
        return None, False
    client = groq.Client(api_key=api_key)
    try:
        # warm-up call (very small)
        client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hola"}],
            temperature=0.1,
            max_tokens=2
        )
        return client, True
    except Exception as e:
        st.error(f"Error Groq init: {e}")
        return None, False

client, is_connected = init_groq_client()
if not is_connected:
    st.stop()

# ---- Session state defaults ----
defaults = {
    "messages": [],
    "conversation_id": None,
    "session_key": str(uuid.uuid4())[:8],
    "speech_text": "",
    "to_send": None,
    "sending": False,
    "client": client
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---- Get spoken_text from URL (if redirected by browser recognition) ----
params = st.query_params
spoken = params.get("spoken_text", "")
spoken = urllib.parse.unquote(spoken) if spoken else ""
if spoken:
    # Put it into session state and clear query params
    st.session_state.speech_text = spoken
    st.session_state.to_send = spoken
    # clear the query params so a refresh doesn't re-trigger
    try:
        st.experimental_set_query_params()
    except Exception:
        # some Streamlit versions may not support; ignore if fails
        pass

# ---- UI Header ----
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# ---- Chat history (single source of truth) ----
# Render messages from session_state.messages only
for msg in st.session_state.messages:
    role = msg.get("role", "Tu")
    content = msg.get("content", "")
    st.markdown(f"**{role}:** {content}")

# ---- Input field (prefill with speech_text if present) ----
input_key = f"input_text_{st.session_state.session_key}"
user_input = st.text_input("Tu:", key=input_key, value=st.session_state.speech_text)

# ---- Microphone button (single stable component) ----
# JS stops automatically on silence via onspeechend and redirects only when a result exists.
components.html("""
<div style="margin-top:10px;">
  <button id="mic" style="font-size:0.95em; padding:0.25em 0.8em; cursor:pointer;">🎤 Parla</button>
  <span id="debug_text" style="font-size:0.95em; margin-left:0.6em; color:#555;"></span>
</div>
<script>
  const mic = document.getElementById("mic");
  const debug = document.getElementById("debug_text");

  mic.onclick = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      debug.innerText = "⚠️ El navegador no suporta SpeechRecognition.";
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'ca-ES';
    recognition.interimResults = false; // do not flood with partials
    recognition.maxAlternatives = 1;
    recognition.continuous = false; // stop on silence

    debug.innerText = "🎙️ Escoltant...";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      debug.innerText = "🔊 " + transcript;
      // small delay so user sees the "has said" text, then redirect with param
      setTimeout(() => {
        const currentUrl = window.location.pathname;
        window.location.href = currentUrl + "?spoken_text=" + encodeURIComponent(transcript);
      }, 250);
    };

    recognition.onspeechend = () => {
      // stop automatically when the user stops speaking
      try { recognition.stop(); } catch(e) {}
      debug.innerText = "⏹️ Enregistrament finalitzat.";
    };

    recognition.onerror = (e) => {
      debug.innerText = "⚠️ Error reconeixement: " + (e.error || "unknown");
    };

    recognition.onend = () => {
      // if no result happened, give a hint
      if (!debug.innerText.startsWith("🔊")) {
        debug.innerText = "⏹️ No s'ha detectat veu.";
      }
    };

    recognition.start();
  };
</script>
""", height=100)

# ---- Audio helper functions ----
def generate_audio_base64(text: str) -> str:
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio_sequence(text: str):
    # split into sentences and play them sequentially
    if isinstance(text, str):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    else:
        sentences = list(text)
    for s in sentences:
        if not s.strip():
            continue
        b64 = generate_audio_base64(s)
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        components.html(audio_html, height=0)
        # reasonable pause after sentence
        pause = min(4.0, max(0.6, 0.25 * len(s.split())))
        time.sleep(pause)

# ---- Send / handle message logic (no printing here) ----
def handle_send(msg: str):
    """Appends user message, calls backend, appends bot reply, plays audio, reruns once."""
    if not msg or st.session_state.get("sending"):
        return

    st.session_state.sending = True
    # append user message (history source)
    st.session_state.messages.append({"role": "Tu", "content": msg})

    # call backend
    try:
        r = requests.post("https://batllori-chat.onrender.com/chat", json={
            "message": msg,
            "conversation_id": st.session_state.conversation_id
        }, timeout=20)
        rj = r.json()
        bot_response = rj.get("response", "❌ Error")
        # remove think blocks safely
        bot_response = re.sub(r"\s*<think\b[^>]*>.*?</think>\s*", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
        st.session_state.conversation_id = rj.get("conversation_id", None)
    except Exception as e:
        bot_response = f"❌ Error: {e}"

    # append bot reply to history (single source)
    st.session_state.messages.append({"role": "BatllorIA", "content": bot_response})

    # play reply audio (non-blocking-ish)
    try:
        play_audio_sequence(bot_response)
    except Exception:
        # if TTS fails, ignore and continue
        pass

    # cleanup
    st.session_state.speech_text = ""
    st.session_state.to_send = None
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.session_state.sending = False

    # finally rerun so the page re-renders showing the new history (no duplicated prints)
    st.experimental_rerun()

# ---- Auto-send if we have a to_send from the microphone redirect ----
if st.session_state.to_send and not st.session_state.sending:
    # handle_send will set sending and rerun; keep this guard so it runs exactly once
    handle_send(st.session_state.to_send)

# ---- Manual send button (user typed) ----
if st.button("Envia") and user_input.strip():
    handle_send(user_input.strip())

# ---- Reset chat ----
if st.button("Reiniciar conversa"):
    try:
        requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
    except Exception:
        pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.speech_text = ""
    st.session_state.to_send = None
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.experimental_rerun()
