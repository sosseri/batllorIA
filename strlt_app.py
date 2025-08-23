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
st.set_page_config(
    page_title="Xat amb BatllorIA",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="auto"
)


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
        # create a space to place the waiting message
        spinner_placeholder = st.empty()
        with st.spinner("⏳ ❗La primera interacció pot trigar fins a 1 minut❗️ Perdona l'espera!"):
            response = requests.post(
                "https://batllori-chat.onrender.com/chat",
                json={
                    "message": user_message.strip(),
                    "conversation_id": st.session_state.conversation_id
                },
                timeout=120  # wait up to 2 minutes
            )
        data = response.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"
    finally: 
        # 👇 clear spinner when done 
        spinner_placeholder.empty()

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

# Helper: send pre-suggested question
def send_suggested(q: str):
    process_message(q)

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
    .suggestions { margin-top: 0.6rem; display:flex; flex-wrap:wrap; gap:0.4rem; }
    .suggestion-btn { background:#f1f1f1; border:none; padding:6px 12px; border-radius:12px; cursor:pointer; font-size:0.9rem; }
    .suggestion-btn:hover { background:#e1e1e1; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💬 Xat amb BatllorIA</h1>
    <h2>La Intel•ligència Artificial de la família Batllori</h2>
    <div class="badge">🎉 Festa Major de Sants 2025 🎉</div>
</div>
""", unsafe_allow_html=True)

# ---------- WELCOME ----------
if not st.session_state.messages:
#    st.markdown("<small>❗La primera interacció pot trigar fins a 1 minut❗️</small>", unsafe_allow_html=True)
#    st.markdown("### 🎭 Benvingut a la Festa de Sants! ")
#    st.markdown("Pregunta'm qualsevol cosa sobre la festa major del barri.")
    st.markdown("### 🎭 Benvingut a la Festa Major de Sants!")
    st.markdown("Pots preguntar-me sobre:\n"
            "- 🎨 El **guarnit** del carrer Papin i com està fet.\n"
            "- 👨‍👩‍👧‍👦 La família **Batllori** i la seva història.\n"
            "- 🏠 Els altres **carrers** que participen i les seves decoracions.\n"
            "- 📅 El **programa** d’activitats del carrer Papin i d'altres carrers.\n"
            "- 🙋‍♂️ Com **participar** a la comissió de festa major del Carrer Papin.\n"
        )


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

# ---------- Suggested questions (only before first message) ----------
if not st.session_state.messages:
    st.markdown("<div class='suggestions'>", unsafe_allow_html=True)
    suggestions = [
        "Quin és el tema del carrer Papin?",
        "Podries explicar-me el guarnit d’aquest any?",
        "Qui és la família Batllori?",
        "Quins són els altres carrers de la festa?",
        "Què hi ha avui al carrer Papin?",
        "Què hi ha demà al carrer Papin?",
        "Què hi ha avui a la Festa Major de Sants?",
        "Com puc participar a la comissió de festes?"
    ]
    for i, q in enumerate(suggestions):
        st.button(q, key=f"sugg_{i}", on_click=send_suggested, args=(q,), use_container_width=False)
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
st.markdown("""
<div class='footer-note'>
    🔊 Clica l'altaveu per escoltar les respostes 🔊
</div>
""", unsafe_allow_html=True)

import streamlit as st

st.markdown("""
<style>
.disclaimer-card{
  border-radius: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(0,0,0,.08);
  background: linear-gradient(180deg, rgba(255,255,255,.7), rgba(255,255,255,.5));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  box-shadow: 0 8px 24px rgba(0,0,0,.06);
  margin: 8px 0 18px 0;
}
.disclaimer-title{
  display:flex; gap:.5rem; align-items:center;
  font-weight: 700; font-size: .95rem; margin: 0 0 6px 0;
}
.disclaimer-text{
  font-size: .85rem; line-height: 1.4; margin: 0;
}

/* Modo oscuro */
@media (prefers-color-scheme: dark) {
  .disclaimer-card{
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
    border: 1px solid rgba(255,255,255,.18);
    box-shadow: 0 8px 24px rgba(0,0,0,.35);
    position: sticky; bottom: 8px; z-index: 999;
  }
}
</style>

<div class="disclaimer-card">
  <div class="disclaimer-title">🤖 Avis de la festa</div>
  <p class="disclaimer-text">
    Aquesta és una intel·ligència artificial feta per la Festa Major de Sants. 🎉
    🕵️ Pot generar informació incorrecta i no ens fem responsables de l’ús inadequat
    que en puguin fer adults massa esverats o criatures 🎈.
    🍻 Pren-t’ho amb esperit festiu i, si tens dubtes seriosos, pregunta a la comissió! 🍻
  </p>
</div>
""", unsafe_allow_html=True)

