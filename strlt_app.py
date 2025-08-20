# ---------- PROCESS MESSAGE (send to backend, DO NOT generate audio) ----------
def process_message(user_message: str):
    if not user_message.strip() or st.session_state.processing:
        return

    st.session_state.processing = True

    # append user message
    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "user",
        "content": user_message.strip()
    })

    # Call backend (this may take time)
    bot_response = "❌ Error: no response"
    try:
        response = requests.post(
            "https://batllori-chat.onrender.com/chat",
            json={
                "message": user_message.strip(),
                "conversation_id": st.session_state.conversation_id
            },
            timeout=60  # ⬅️ increased to 1 minute
        )
        data = response.json()
        bot_response = data.get("response", "❌ Error de connexió")
        st.session_state.conversation_id = data.get("conversation_id")

        # Remove any <think> blocks if present
        bot_response = re.sub(r"<think.*?>.*?</Thinking>", "", bot_response, flags=re.DOTALL | re.IGNORECASE)
    except Exception as e:
        bot_response = f"❌ Error: {str(e)}"

    # append bot message
    st.session_state.messages.append({
        "id": uuid.uuid4().hex,
        "role": "bot",
        "content": bot_response,
        "audio_b64": None
    })

    st.session_state.processing = False


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
