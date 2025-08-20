import streamlit as st
import requests
from gtts import gTTS
from io import BytesIO
import base64
import re
import streamlit.components.v1 as components
import uuid
import html
import requests

# -------------------------------
# Reset function (safe callback)
# -------------------------------
def reset_conversation():
    """
    Safely reset conversation-related session state.
    This runs inside a button callback (safe context for mutating session_state).
    """
    conv_id = st.session_state.get("conversation_id")
    if conv_id:
        try:
            requests.delete(f"https://batllori-chat.onrender.com/conversations/{conv_id}", timeout=5)
        except Exception:
            pass

    st.session_state["messages"] = []
    st.session_state["conversation_id"] = None
    st.session_state["processing"] = False
    st.session_state["user_input"] = ""
    st.rerun()


# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Xat amb BatllorIA", page_icon="💬", layout="centered")

# ---------- SESSION STATE INIT ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "play_request" not in st.session_state:
    st.session_state.play_request = None
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# ---------- HELPER: TTS -> base64 ----------
def generate_audio_base64(text: str) -> str:
    tts = gTTS(text=text, lang='ca')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ---------- PROCESS MESSAGE ----------
def process_message(user_message: str):
    if not user_message.strip() or st.session_state.processing:
        return

    st.session_state.processing = True

    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": user_message.strip()
    })

    bot_response = "❌ Error: no response"
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat",
            json={
                "message": user_message.strip(),
                "conversation_id": st.session_state.conversation_id
            },
            timeout=60  # ⬅️ wait up to 1 minute
        )
        data = response.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"

    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "bot",
        "content": bot_response,
        "audio_b64": None
    })

    st.session_state.processing = False

# ---------- SEND CALLBACK ----------
def send_callback():
    text = st.session_state.get("user_input", "").strip()
    if not text:
        return
    process_message(text)
    st.session_state.user_input = ""

# ---------- UI: Header and CSS ----------
st.markdown("""
<style>
    body { background-color: #fafafa; font-family: 'Helvetica Neue', sans-serif; }
    .main-header { background: url('https://upload.wikimedia.org/wikipedia/commons/0/0c/Azulejo_pattern.svg'); background-size: cover; background-position: center; border-radius: 16px; padding: 2rem; text-align: center; color: #222; margin-bottom: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header h2 { margin-top: 0.5rem; font-weight: 400; color: #444; }
    .badge { display: inline-block; margin-top: 0.8rem; padding: 0.3rem 0.8rem; background: #ffeed9; color: #d35400; border-radius: 12px; font-size: 0.9rem; font-weight: 600; }
    .chat-bubble-user { background: #e1f5fe; padding: 0.7rem 1rem; border-radius: 16px; margin: 0.4rem 0; max-width: 80%; align-self: flex-end; margin-left: auto; }
    .chat-bubble-bot { background: #fff3e0; padding: 0.7rem 1rem; border-radius: 16px; margin: 0.4rem 0; max-width: 80%; align-self: flex-start; margin-right: auto; }
    .small-note { color: #666; font-size: 0.9rem; }
    .play-button { border: none; background: transparent; cursor: pointer; font-size: 1.1rem; }
    .input-row { display:flex; gap:8px; align-items:center; }
    .send-btn { padding:8px 12px; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💬 Xat amb BatllorIA</h1>
    <h2>L'Intelligència Artificial de la família Batllori</h2>
    <div class="badge">🎉 Festa Major de Sants 2025 🎉</div>
</div>
""", unsafe_allow_html=True)

# ---------- WELCOME ----------
if not st.session_state.messages:
    st.markdown("### 🎭 Benvingut a la Festa de Sants! ")
    st.markdown("Pregunta'm qualsevol cosa sobre la festa major del barri.")

# ---------- Render chat messages ----------
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>🧑 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)
    else:
        cols = st.columns([0.95, 0.05])
        with cols[0]:
            st.markdown(f"<div class='chat-bubble-bot'>🤖 {html.escape(msg['content'])}</div>", unsafe_allow_html=True)
        with cols[1]:
            def make_on_click(mid=msg['id']):
                def _cb():
                    st.session_state.play_request = mid
                return _cb
            st.button("🔊", key=f"play_{msg['id']}", help="Click to synthesize and play this message", on_click=make_on_click())

# ---------- If user requested to play a message ----------
if st.session_state.play_request:
    play_id = st.session_state.play_request
    target = None
    for m in st.session_state.messages:
        if m['id'] == play_id and m['role'] == 'bot':
            target = m
            break

    if target is None:
        st.warning("Requested message not found.")
        st.session_state.play_request = None
    else:
        if target.get('audio_b64'):
            audio_b64 = target['audio_b64']
        else:
            with st.spinner('Generating audio...'):
                try:
                    sanitized = target['content'].replace('*', '').replace('#', '')
                    audio_b64 = generate_audio_base64(sanitized)
                    target['audio_b64'] = audio_b64
                except Exception as e:
                    st.error(f"TTS generation failed: {e}")
                    st.session_state.play_request = None
                    audio_b64 = None

        if audio_b64:
            audio_element_id = f"audio_{target['id']}"
            status_id = f"status_{target['id']}"
            player_html = f"""
            <div style='display:flex; align-items:center; gap:12px;'>
                <div style='font-size:1.4rem;'>🔊</div>
                <div>
                    <div style='font-size:0.95rem; color:#333'> </div>
                    <div id='{status_id}' style='color:#666; font-size:0.9rem; display:none;'>Llegint...</div>
                    <audio id='{audio_element_id}' autoplay>
                        <source src='data:audio/mp3;base64,{audio_b64}' type='audio/mp3'>
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>
            <script>
            (function() {{
                const audio = document.getElementById('{audio_element_id}');
                const status = document.getElementById('{status_id}');
                function show() {{ status.style.display = 'block'; }}
                function hide() {{ status.style.display = 'none'; }}
                audio.addEventListener('play', function() {{ show(); }});
                audio.addEventListener('ended', function() {{ hide(); }});
                audio.addEventListener('pause', function() {{ hide(); }});
                setTimeout(()=>{{ show(); }}, 50);
            }})();
            </script>
            """
            components.html(player_html, height=120)
            st.session_state.play_request = None

# ---------- INPUT ROW ----------
st.markdown("<div class='input-row'>", unsafe_allow_html=True)
cols = st.columns([4,1])
with cols[0]:
    st.text_input("Escriu el teu missatge...", key="user_input", placeholder="Escriu... i premi Envia")
with cols[1]:
    st.button("📨 Envia", key="send_button", on_click=send_callback, args=())
st.markdown("</div>", unsafe_allow_html=True)

if st.button("🔄 Reiniciar conversa", on_click=reset_conversation):
    pass

# ---------- PROCESSING INDICATOR ----------
if st.session_state.processing:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; font-size:1rem; color:#444;">
        <span>🤖 Processant la pregunta</span>
        <span class="dot-anim">.</span>
        <span class="dot-anim">.</span>
        <span class="dot-anim">.</span>
    </div>
    <style>
    @keyframes blink {
        0% { opacity: 0.2; }
        20% { opacity: 1; }
        100% { opacity: 0.2; }
    }
    .dot-anim {
        animation: blink 1.4s infinite both;
        font-weight: bold;
    }
    .dot-anim:nth-child(2) { animation-delay: 0.2s; }
    .dot-anim:nth-child(3) { animation-delay: 0.4s; }
    </style>
    """, unsafe_allow_html=True)

# ---------- Footer note ----------
st.markdown(
    "<div class='footer-note'>Clica l'altaveu per llegir les respostes. "
    "ℹ️ La primera resposta pot trigar fins a <b>1 minut</b>.</div>",
    unsafe_allow_html=True,
)
