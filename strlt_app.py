import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import streamlit.components.v1 as components
import uuid
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- INIT STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- FUNCTIONS ----------
def speak_text(text):
    try:
        tts = gTTS(text=text, lang="ca")
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        audio_base64 = base64.b64encode(audio_fp.read()).decode("utf-8")
        audio_html = f"""
            <audio autoplay="true" controls="controls">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Text-to-Speech error: {e}")

def query_bot(prompt, session_id="default"):
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"prompt": prompt, "session_id": session_id},
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get("response", "Error: empty response")
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Request failed: {e}"

# ---------- UI ----------
st.title("💬 Xat amb BatllorIA")

# Show chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input box
if prompt := st.chat_input("Escriu la teva pregunta aquí..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Bot typing simulation
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        with st.spinner("El BatllorIA està pensant..."):
            bot_response = query_bot(prompt, session_id="demo")

        # Clean response (remove think blocks if any)
        bot_response = re.sub(
            r"\s*<think\b[^>]*>.*?</think>\s*",
            "",
            bot_response,
            flags=re.DOTALL | re.IGNORECASE,
        )

        for chunk in bot_response.split():
            full_response += chunk + " "
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.03)

        message_placeholder.markdown(full_response)

        # Add bot response to state
        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # Speak bot response
        speak_text(full_response)

# ---------- Suggested Questions ----------
if len(st.session_state.messages) == 0:
    st.markdown("### 💡 Preguntes suggerides")
    suggested = [
        "Quin és el tema del carrer Papin?",
        "Qui és la família Batllori?",
        "Quines són les altres vies de la festa?",
        "Què hi ha avui al carrer Papin?",
        "Què hi ha demà al carrer Papin?"
    ]

    cols = st.columns(len(suggested))
    for i, q in enumerate(suggested):
        if cols[i].button(q):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()
