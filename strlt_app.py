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

# Streamlit config
st.set_page_config(page_title="Xat amb Batllori", page_icon="🧠")

# Titoli
st.header("💬 Xat amb BatllorIA")
st.subheader("L'Intelligència Artificial de la família Batllori")

# Init session state
for key, default in {
    "messages": [],
    "conversation_id": None,
    "session_key": str(uuid.uuid4())[:8],
    "spoken_text": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Handle spoken_text from URL (JS)
params = st.query_params
spoken = params.get("spoken_text", "")
if spoken:
    spoken_text = urllib.parse.unquote(spoken)
    st.session_state.spoken_text = spoken_text
    st.session_state.input_text = spoken_text
    st.query_params.clear()

# Show chat history
for message in st.session_state.messages:
    st.markdown(f"**{message['role']}:** {message['content']}")

# Campo input (riempito dalla voce se presente)
user_input = st.text_input("Tu:", key="input_text", value=st.session_state.get("spoken_text", ""))
st.session_state.spoken_text = ""

# Microfono via JS
components.html("""
<script>
  const existing = document.getElementById("mic");
  if (!existing) {
    const mic = document.createElement("button");
    mic.id = "mic";
    mic.innerText = "🎤 Parla";
    mic.style.fontSize = "1.2em";
    mic.style.marginTop = "10px";
    mic.style.background = "none";
    mic.style.border = "none";
    mic.style.cursor = "pointer";
    document.body.appendChild(mic);

    mic.onclick = () => {
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.lang = 'ca-ES';
      recognition.interimResults = false;
      recognition.start();

      recognition.onstart = () => { mic.innerText = "🎙️ Escoltant..."; };
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const url = new URL(window.location.href);
        url.searchParams.set("spoken_text", transcript);
        window.location.href = url.toString();
      };
      recognition.onerror = () => { mic.innerText = "🎤 Error"; };
      recognition.onend = () => { if (mic.innerText !== "🎤 Error") mic.innerText = "🎤 Parla"; };
    };
  }
</script>
""", height=0)

# Audio generation
def generate_audio_base64(text):
    tts = gTTS(text=text, lang='ca')
    fp = BytesIO(); tts.write_to_fp(fp); fp.seek(0)
    return base64.b64encode(fp.read()).decode()

def play_audio_sequence(sentences):
    if isinstance(sentences, str):
        sentences = re.split(r'(?<=[.!?])\s+', sentences.strip())
    for sentence in sentences:
        b64 = generate_audio_base64(sentence)
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        components.html(audio_html, height=0)
        time.sleep(min(5, len(sentence.split()) * 0.6))

# Invio messaggio
send_button_key = f"send_button_{st.session_state.session_key}"
if st.button("Envia", key=send_button_key) and user_input.strip():
    user_msg = user_input.strip()
    st.session_state.messages.append({"role": "Tu", "content": user_msg})

    # Richiesta al backend
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat",
            json={"message": user_msg, "conversation_id": st.session_state.conversation_id},
            timeout=30
        )
        response_data = response.json()
        bot_response = response_data["response"]
        st.session_state.conversation_id = response_data.get("conversation_id")
    except Exception as e:
        bot_response = f"❌ Error: {e}"

    st.session_state.messages.append({"role": "BatllorIA", "content": bot_response})
    st.markdown("**Tu:** " + user_msg)
    st.markdown("**Batllori:** " + bot_response)

    play_audio_sequence(bot_response)

    # Reset campo input e chiave
    st.session_state.input_text = ""
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()

# Pulsante reset
reset_button_key = f"reset_button_{st.session_state.session_key}"
if st.button("Reiniciar conversa", key=reset_button_key):
    if st.session_state.conversation_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{st.session_state.conversation_id}")
        except:
            pass
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.input_text = ""
    st.session_state.session_key = str(uuid.uuid4())[:8]
    st.rerun()
