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
            timeout=60  # wait up to 1 minute
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

# Helper: send pre-suggested question
def send_suggested(q: str):
    process_message(q)

# ---------- UI: Header and CSS ----------
st.markdown("""
<style>
    body { 
        background-color: #f8fafc; 
        font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; 
    }
    .main-header { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px; 
        padding: 2.5rem; 
        text-align: center; 
        color: white; 
        margin-bottom: 2rem; 
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .main-header h1 { 
        margin: 0; 
        font-size: 2.2rem; 
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .main-header h2 { 
        margin-top: 0.5rem; 
        font-weight: 300; 
        color: rgba(255,255,255,0.9); 
        font-size: 1.1rem;
    }
    .badge { 
        display: inline-block; 
        margin-top: 1rem; 
        padding: 0.5rem 1.2rem; 
        background: rgba(255,255,255,0.2); 
        color: white; 
        border-radius: 25px; 
        font-size: 1rem; 
        font-weight: 600;
        backdrop-filter: blur(10px);
    }
    
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .message-wrapper {
        display: flex;
        margin: 1rem 0;
        align-items: flex-start;
        gap: 0.5rem;
    }
    
    .message-wrapper.user {
        justify-content: flex-end;
    }
    
    .message-wrapper.bot {
        justify-content: flex-start;
    }
    
    .chat-bubble-user { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem; 
        border-radius: 20px 20px 5px 20px; 
        max-width: 75%; 
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        font-size: 0.95rem;
        line-height: 1.4;
    }
    
    .chat-bubble-bot { 
        background: white;
        color: #2d3748;
        padding: 1rem 1.5rem; 
        border-radius: 20px 20px 20px 5px; 
        max-width: 75%; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        font-size: 0.95rem;
        line-height: 1.4;
        position: relative;
    }
    
    .audio-button {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.9rem;
        margin-top: 0.5rem;
        flex-shrink: 0;
    }
    
    .audio-button:hover {
        background: #edf2f7;
        border-color: #cbd5e0;
        transform: scale(1.05);
    }
    
    .input-section {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    
    .input-row { 
        display: flex; 
        gap: 12px; 
        align-items: flex-end;
        margin-bottom: 1rem;
    }
    
    .send-btn { 
        padding: 12px 20px; 
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        white-space: nowrap;
    }
    
    .send-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .suggestions-section {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
    }
    
    .suggestions-title {
        font-size: 0.9rem;
        color: #718096;
        margin-bottom: 0.8rem;
        font-weight: 500;
    }
    
    .suggestions { 
        display: flex; 
        flex-wrap: wrap; 
        gap: 0.5rem; 
    }
    
    .suggestion-btn { 
        background: #f7fafc;
        color: #4a5568;
        border: 1px solid #e2e8f0;
        padding: 8px 16px; 
        border-radius: 20px; 
        cursor: pointer; 
        font-size: 0.9rem;
        transition: all 0.2s ease;
        white-space: nowrap;
    }
    
    .suggestion-btn:hover { 
        background: #edf2f7;
        border-color: #cbd5e0;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .welcome-section {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    
    .welcome-section h3 {
        color: #2d3748;
        margin-bottom: 0.5rem;
    }
    
    .welcome-section p {
        color: #718096;
        font-size: 1.1rem;
    }
    
    .reset-button {
        background: #fed7d7;
        color: #c53030;
        border: 1px solid #feb2b2;
        padding: 8px 16px;
        border-radius: 12px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s ease;
        margin-top: 1rem;
    }
    
    .reset-button:hover {
        background: #feb2b2;
        transform: translateY(-1px);
    }
    
    .footer-note { 
        color: #718096; 
        font-size: 0.85rem; 
        text-align: center;
        margin-top: 1.5rem;
        padding: 1rem;
        background: #f7fafc;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    
    .processing-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    @keyframes blink {
        0% { opacity: 0.2; }
        20% { opacity: 1; }
        100% { opacity: 0.2; }
    }
    .dot-anim {
        animation: blink 1.4s infinite both;
        font-weight: bold;
        color: #667eea;
    }
    .dot-anim:nth-child(2) { animation-delay: 0.2s; }
    .dot-anim:nth-child(3) { animation-delay: 0.4s; }
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
    st.markdown("""
    <div class="welcome-section">
        <h3>🎭 Benvingut a la Festa de Sants!</h3>
        <p>Pregunta'm qualsevol cosa sobre la festa major del barri.</p>
    </div>
    """, unsafe_allow_html=True)

# ---------- Render chat messages ----------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class='message-wrapper user'>
            <div class='chat-bubble-user'>🧑 {html.escape(msg['content'])}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Create unique key for each bot message audio button
        audio_key = f"audio_{msg['id']}"
        
        st.markdown(f"""
        <div class='message-wrapper bot'>
            <div class='chat-bubble-bot'>🤖 {html.escape(msg['content'])}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Audio button positioned right after the message
        cols = st.columns([1, 10])
        with cols[0]:
            def make_on_click(mid=msg['id']):
                def _cb():
                    st.session_state.play_request = mid
                return _cb
            st.button("🔊", 
                     key=audio_key, 
                     help="Escolta aquest missatge", 
                     on_click=make_on_click(),
                     use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ---------- INPUT SECTION ----------
st.markdown('<div class="input-section">', unsafe_allow_html=True)

st.markdown('<div class="input-row">', unsafe_allow_html=True)
cols = st.columns([5, 1])
with cols[0]:
    st.text_input("Escriu el teu missatge...", 
                 key="user_input", 
                 placeholder="Escriu la teva pregunta aquí...",
                 label_visibility="collapsed")
with cols[1]:
    st.button("📨 Envia", 
             key="send_button", 
             on_click=send_callback, 
             use_container_width=True,
             type="primary")
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Suggested questions (now below input) ----------
if not st.session_state.messages:
    st.markdown('<div class="suggestions-section">', unsafe_allow_html=True)
    st.markdown('<div class="suggestions-title">💡 Preguntes suggerides:</div>', unsafe_allow_html=True)
    st.markdown('<div class="suggestions">', unsafe_allow_html=True)
    suggestions = [
        "Quin és el tema del carrer Papin?",
        "Qui és la família Batllori?",
        "Quines són les altres vies de la festa?",
        "Què hi ha avui al carrer Papin?",
        "Què hi ha demà al carrer Papin?",
    ]
    for i, q in enumerate(suggestions):
        st.button(q, key=f"sugg_{i}", on_click=send_suggested, args=(q,))
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# Reset button
st.button("🔄 Reiniciar conversa", 
         on_click=reset_conversation, 
         help="Comença una nova conversa")

# ---------- PROCESSING INDICATOR ----------
if st.session_state.processing:
    st.markdown("""
    <div class="processing-indicator">
        <span>🤖 Processant la pregunta</span>
        <span class="dot-anim">.</span>
        <span class="dot-anim">.</span>
        <span class="dot-anim">.</span>
    </div>
    """, unsafe_allow_html=True)

# ---------- Footer note ----------
st.markdown("""
<div class='footer-note'>
    🔊 Clica l'altaveu per escoltar les respostes • 
    ℹ️ La primera resposta pot trigar fins a <strong>1 minut</strong>
</div>
""", unsafe_allow_html=True)
