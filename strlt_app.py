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

# Config
st.set_page_config(page_title="Xat amb Batllori", page_icon="🧠")

# Titolo
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# Init state
for key, default in {
    "messages": [],
    "conversation_id": None,
    "session_key": str(uuid.uuid4())[:8],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Get spoken_text from URL
params = st.query_params
spoken = params.get("spoken_text", "")
spoken = urllib.parse.unquote(spoken) if spoken else ""

# Pulizia parametri URL
if spoken:
    st.query_params.clear()

# Mostra cronologia
for msg in st.session_state.messages:
    st.markdown(f"**{msg['role']}:** {msg['content']}")

# Input field (usa spoken_text solo se presente)
default_input = spoken if spoken else ""
input_key = f"input_text_{st.session_state.session_key}"
user_input = st.text_input("Tu:", key=input_key, value=default_input)

# Microfono: bottone visibile che modifica l’URL
components.html("""
<div style="margin:10px 0;">
  <button id="mic" style="font-size:1.2em; padding:0.4em 1em; cursor:pointer;">🎤 Parla</button>
</div>
<script>
const mic = document.getElementById("mic");
mic.onclick = () => {
  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = 'ca-ES';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.start();

  recognition.onstart = () => {
    mic.innerText = "🎙️ Escoltant...";
  };
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    const url = new URL(window.location.href);
    url.searchParams.set("spoken_text", transcript);
    window.location.href = url.toString();
  };
  recognition.onerror = () => { mic.innerText = "🎤 Error"; };
  recognition.onend = () => {
    if (mic.innerText !== "🎤 Error") mic.innerText = "🎤 Parla";
  };
};
</script>
""", height=70)

# Funzioni audio
def generate_audio_base64(text):
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio_sequence(sentences):
    if isinstance(sentences, str):
        sentences = re.split(r'(?<=[.!?])\s+', sentences.strip())
    for s in sentences:
        b64 = generate_audio_base64(s)
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        components.html(audio_html, height=0)
        time.sleep(min(5, len(s.split()) * 0.5))

# Invia messaggio
if st.button("Envia") and user_input.strip():
    user_msg = user_input.strip()
    st.session_state.messages.append({"role": "Tu", "content": user_msg})

    try:
        r = requests.post("https://batllori-chat.onrender.com/chat", json={
            "message": user_msg,
            "conversation_id": st.session_state.conversation_id
        })
        rj = r.json()
        bot_response = rj.get("response", "❌ Error")
        st.session_state.conversation_id = rj.get("conversation_id", None)
    except Exception as e:
        bot_response = f"❌ Error: {e}"

    st.session_state.messages.append({"role": "BatllorIA", "content": bot_response})
    st.markdown("**Tu:** " + user_msg)
    st.markdown("**Batllori:** " + bot_response)
    play_audio_sequence(bot_response)

    # Reset via nuova session_key (per forzare reset del campo input)
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()

# Reset chat
if st.button("Reiniciar conversa"):
    try:
        requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
    except:
        pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()
