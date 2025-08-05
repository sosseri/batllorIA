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
from groq import Groq
import tempfile

# Config
st.set_page_config(page_title="Xat amb Batllori", page_icon="💬")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("🤖 Errore: manca GROQ_API_KEY nei Segreti!")

# Titolo
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# Init state
for key, default in {
    "messages": [],
    "conversation_id": None,
    "session_key": str(uuid.uuid4())[:8],
    "speech_text": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Get spoken_text from URL
params = st.query_params
spoken = params.get("spoken_text", "")
spoken = urllib.parse.unquote(spoken) if spoken else ""

# Pulizia parametri URL
if spoken:
    st.session_state.speech_text = spoken
    st.query_params.clear()

# Mostra cronologia
for msg in st.session_state.messages:
    st.markdown(f"**{msg['role']}:** {msg['content']}")

# Input field (usa speech_text se presente, altrimenti vuoto)
default_input = st.session_state.speech_text if st.session_state.speech_text else ""
input_key = f"input_text_{st.session_state.session_key}"
user_input = st.text_input("Tu:", key=input_key, value=default_input)

# Microfono + trascrizione - renderizza solo se non c'è speech_text in attesa
if not st.session_state.speech_text:
    components.html("""
    <div style="margin-top:10px;">
      <button id="mic" style="font-size:1.3em; padding:0.5em 1.5em; cursor:pointer;">🎤 Parla</button>
      <p id="debug_text" style="font-size:1em; font-style:italic; color:#555;"></p>
    </div>
    <script>
      const mic = document.getElementById("mic");
      const debug = document.getElementById("debug_text");

      mic.onclick = () => {
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'ca-ES';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.start();
        debug.innerText = "🎙️ Escoltant...";

        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          debug.innerText = "🔊 Has dit: " + transcript;

          // Redirect invece di postMessage
          setTimeout(() => {
            const currentUrl = window.location.pathname;
            window.location.href = currentUrl + "?spoken_text=" + encodeURIComponent(transcript);
          }, 1500);
        };

        recognition.onerror = () => {
          debug.innerText = "⚠️ Error durant el reconeixement de veu.";
        };

        recognition.onend = () => {
          if (!debug.innerText.startsWith("🔊")) {
            debug.innerText = "⏹️ No s'ha detectat veu.";
          }
        };
      };
    </script>
    """, height=130)
else:
    # Mostra messaggio di conferma quando c'è testo trascritto
    st.success(f"🎤 Testo trascritto: '{st.session_state.speech_text}' - Modifica se necessario e premi Envia")

# Funzioni audio
def generate_audio_base64_drop(text):
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def play_audio_sequence_drop(sentences):
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

def generate_audio_base64(text):
    tts = gTTS(text=text, lang='ca')
    audio_fp = BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return base64.b64encode(audio_fp.read()).decode()

def play_audio_sequence(sentences):
    if type(sentences) == list:
        for sentence in sentences:
            audio_b64 = generate_audio_base64(sentence)
            audio_html = f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            """
            components.html(audio_html, height=0)
            # Adjust pause duration: shorter for short sentences, minimal base pause
            pause_duration = len(sentence.split()) * (0.5/(np.mean([len(x) for x in sentence.split()]))*5)
            time.sleep(pause_duration)
    else:
        sentence = sentences
        audio_b64 = generate_audio_base64(sentence)
        audio_html = f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            """
        components.html(audio_html, height=0)
        pause_duration = len(sentence.split()) * (0.5/(np.mean([len(x) for x in sentence.split()]))*5)
        time.sleep(pause_duration)
        
    # Clear the input field after audio finishes playing
    st.session_state.temp_speech_input = ""


def read_aloud_groq(text: str, voice_id: str = "Celeste-PlayAI") -> BytesIO:
    """
    Text-to-speech usando Groq: crea un WAV temporaneo, lo legge in memoria e torna un BytesIO.
    """
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ Manca la chiave GROQ_API_KEY nei Segreti o vars!")

    client = Groq(api_key=api_key)

    # Synthesize speech via Groq
    response = client.audio.speech.create(
        model="playai-tts",
        voice=voice_id,
        input=text,
        response_format="wav"
    )
    # Scrive su file temporaneo
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    response.write_to_file(tmp_path)  # richiede path su disco :contentReference[oaicite:2]{index=2}

    # Carica in BytesIO
    buf = BytesIO()
    with open(tmp_path, "rb") as f:
        buf.write(f.read())
    buf.seek(0)

    # Rimuovi file temporaneo
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    return buf

import streamlit.components.v1 as components
import base64

def play_audio_button(audio_buf, label="▶️ Escolta"):
    """
    Mostra un bottone che, al click, riproduce un audio WAV.
    Funziona anche su mobile + Streamlit Cloud.
    """
    audio_base64 = base64.b64encode(audio_buf.read()).decode("utf-8")
    html_code = f"""
    <audio id="batllori_audio" src="data:audio/wav;base64,{audio_base64}"></audio>
    <button onclick="document.getElementById('batllori_audio').play()" style="
        font-size: 1.2em;
        margin-top: 1em;
        padding: 0.4em 1.2em;
        background-color: #efefef;
        border: 1px solid #ccc;
        border-radius: 6px;
        cursor: pointer;
    ">{label}</button>
    """
    components.html(html_code, height=80)




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
    ## groq text to speech
    #audio_buf = read_aloud_groq(bot_response, voice_id="Celeste-PlayAI")
    #play_audio_button(audio_buf)
    #st.write(f"🎧 Audio ricevuto: {len(audio_buf.getbuffer())} bytes")

    #free service robotic voice
    play_audio_sequence(bot_response)

    # Reset del testo vocale e session_key
    st.session_state.speech_text = ""
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
    st.session_state.speech_text = ""
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()
