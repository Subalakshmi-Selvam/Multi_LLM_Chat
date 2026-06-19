import streamlit as st
import requests
from datetime import datetime, timezone
from chatbot_ui.core.config import config

st.set_page_config(page_title="Multi-LLM Chat", page_icon="💬", layout="wide")

PROVIDER_MODELS = {
    "Groq": ["llama-3.3-70b-versatile"],
    "Google": ["gemini-2.5-flash"],
}

PROVIDER_COLORS = {
    "Groq": "#F55036",
    "Google": "#4285F4",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
html { font-size: 16px; }

.stApp { background: #0f1117; color: #e8eaf0; }

[data-testid="stSidebar"] {
    background: #161b27 !important;
    border-right: 1px solid #2a2f3e;
}
[data-testid="stSidebar"] * { color: #c9cdd8 !important; }
[data-testid="stSidebar"] h1 {
    font-size: 1.2rem !important; font-weight: 700 !important;
    color: #e8eaf0 !important; letter-spacing: -0.02em;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stTextArea label {
    font-size: 0.78rem !important; font-weight: 600 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
    color: #7c8399 !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #1a1f2e !important; border: 1px solid #2a2f3e !important;
    border-radius: 8px !important; font-size: 0.95rem !important; color: #dde1ed !important;
}
[data-testid="stSidebar"] h3 {
    font-size: 0.72rem !important; font-weight: 700 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    color: #5a6178 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #1e2435 !important; border: 1px solid #2e3447 !important;
    color: #c9cdd8 !important; border-radius: 8px !important;
    font-size: 0.88rem !important; font-weight: 500 !important;
    padding: 0.45rem 0.9rem !important; transition: all 0.15s ease !important;
    text-align: left !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #252b3d !important; border-color: #3e4560 !important; color: #fff !important;
}

/* Delete button red tint */
button[kind="secondary"] { color: #f87171 !important; }

/* Search box */
[data-testid="stSidebar"] .stTextInput input {
    background: #1a1f2e !important; border: 1px solid #2a2f3e !important;
    border-radius: 8px !important; color: #dde1ed !important;
    font-size: 0.9rem !important; padding: 0.4rem 0.8rem !important;
}

/* Session group label */
.session-group {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #4a5168; padding: 6px 0 2px 2px;
}
.session-meta {
    font-size: 0.72rem; color: #5a6178; margin-top: 1px;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: #161b27 !important; border: 1px solid #1e2435 !important;
    border-radius: 12px !important; padding: 1rem 1.2rem !important;
    margin-bottom: 0.6rem !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] ol,
[data-testid="stChatMessage"] ul,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
    font-size: 1.05rem !important; line-height: 1.75 !important; color: #e8eaf0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: #1a2038 !important; border-color: #252d47 !important;
}
[data-testid="stChatMessage"] code {
    font-size: 0.93rem !important; background: #0d111c !important;
    border-radius: 5px !important; padding: 0.15em 0.4em !important; color: #7dd3fc !important;
}
[data-testid="stChatMessage"] pre {
    background: #0d111c !important; border-radius: 8px !important;
    padding: 1rem !important; font-size: 0.9rem !important;
}
[data-testid="stChatMessage"] pre code {
    color: #e2e8f0 !important;
}
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] b {
    color: #ffffff !important; font-weight: 700 !important;
}
[data-testid="stChatMessage"] em { color: #c9d1e0 !important; }
[data-testid="stChatMessage"] a { color: #7dd3fc !important; }

/* Chat input */
[data-testid="stChatInput"] textarea {
    font-size: 1rem !important; background: #161b27 !important;
    border: 1px solid #2a2f3e !important; border-radius: 10px !important;
    color: #e8eaf0 !important; padding: 0.8rem 1rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #3e4d7a !important; box-shadow: 0 0 0 2px rgba(66,133,244,0.15) !important;
}

h1 { font-size: 1.7rem !important; font-weight: 700 !important;
     color: #e8eaf0 !important; letter-spacing: -0.03em !important; }
hr { border-color: #2a2f3e !important; margin: 0.6rem 0 !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0f1117; }
::-webkit-scrollbar-thumb { background: #2a2f3e; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_call(method, url, **kwargs):
    try:
        response = getattr(requests, method)(url, **kwargs)
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            data = {"message": "Invalid response from server"}
        return (True, data) if response.ok else (False, data)
    except requests.exceptions.ConnectionError:
        return False, {"message": "Could not reach the API. Is it running?"}
    except requests.exceptions.Timeout:
        return False, {"message": "Request timed out."}
    except Exception as e:
        return False, {"message": str(e)}


def load_sessions():
    ok, data = api_call("get", f"{config.API_URL}/sessions")
    return data if ok else []


def load_messages(session_id):
    ok, data = api_call("get", f"{config.API_URL}/sessions/{session_id}/messages")
    return data if ok else []


def delete_session(session_id):
    api_call("delete", f"{config.API_URL}/sessions/{session_id}")


def group_sessions(sessions):
    """Group sessions into Today / Yesterday / This week / Older."""
    now = datetime.now(timezone.utc)
    groups = {"Today": [], "Yesterday": [], "This week": [], "Older": []}
    for s in sessions:
        try:
            dt = datetime.fromisoformat(s["created_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = (now - dt).days
            if delta == 0:
                groups["Today"].append(s)
            elif delta == 1:
                groups["Yesterday"].append(s)
            elif delta <= 7:
                groups["This week"].append(s)
            else:
                groups["Older"].append(s)
        except Exception:
            groups["Older"].append(s)
    return groups


def friendly_time(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.seconds < 60:
            return "just now"
        if delta.seconds < 3600:
            return f"{delta.seconds // 60}m ago"
        if delta.days == 0:
            return f"{delta.seconds // 3600}h ago"
        return dt.strftime("%-d %b")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm ready to help. What's on your mind?"}
    ]
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "provider" not in st.session_state:
    st.session_state.provider = "Groq"
if "model_name" not in st.session_state:
    st.session_state.model_name = "llama-3.3-70b-versatile"
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚡ LLM Chat")

    provider = st.selectbox("Provider", list(PROVIDER_MODELS.keys()),
                            index=list(PROVIDER_MODELS.keys()).index(st.session_state.provider))
    model_name = st.selectbox("Model", PROVIDER_MODELS[provider])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    system_prompt = st.text_area("System Prompt", value="You are a helpful assistant.", height=80)
    use_streaming = st.toggle("Stream responses", value=True)

    st.session_state.provider = provider
    st.session_state.model_name = model_name

    accent = PROVIDER_COLORS.get(provider, "#4285F4")
    st.markdown(
        f"<div style='font-size:0.76rem;color:{accent};font-weight:600;"
        f"background:{accent}18;border:1px solid {accent}33;border-radius:6px;"
        f"padding:3px 10px;display:inline-block;margin:4px 0 8px'>● {provider} active</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # --- New chat + search row ---
    col_new, col_srch = st.columns([1, 1])
    with col_new:
        if st.button("＋ New chat", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.messages = []
            st.session_state.confirm_delete = None
            st.rerun()
    with col_srch:
        search_query = st.text_input("", placeholder="🔍 Search…", label_visibility="collapsed")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # --- Session list ---
    sessions = load_sessions()

    if search_query:
        sessions = [s for s in sessions if search_query.lower() in (s.get("title") or "").lower()]

    if not sessions:
        st.markdown(
            "<div style='font-size:0.85rem;color:#4a5168;text-align:center;padding:16px 0'>"
            "No chats yet</div>", unsafe_allow_html=True
        )
    else:
        groups = group_sessions(sessions)
        for group_name, group_sessions_list in groups.items():
            if not group_sessions_list:
                continue
            st.markdown(f"<div class='session-group'>{group_name}</div>", unsafe_allow_html=True)

            for s in group_sessions_list:
                sid = s["id"]
                label = s.get("title") or "Untitled chat"
                time_str = friendly_time(s.get("created_at", ""))
                is_active = sid == st.session_state.session_id

                # Highlight active session
                if is_active:
                    st.markdown(
                        f"<div style='background:#1e2d50;border:1px solid #2e4070;"
                        f"border-radius:8px;padding:6px 10px;margin-bottom:2px'>"
                        f"<div style='font-size:0.88rem;font-weight:600;color:#93b4ff'>"
                        f"💬 {label}</div>"
                        f"<div class='session-meta'>{time_str}</div></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    col_btn, col_del = st.columns([5, 1])
                    with col_btn:
                        if st.button(f"💬 {label}", key=f"s-{sid}", use_container_width=True):
                            st.session_state.session_id = sid
                            history = load_messages(sid)
                            st.session_state.messages = [
                                {"role": m["role"], "content": m["content"]} for m in history
                            ]
                            st.session_state.confirm_delete = None
                            st.rerun()
                    with col_del:
                        if st.button("🗑", key=f"del-{sid}", help="Delete this chat"):
                            st.session_state.confirm_delete = sid

                # Inline confirm delete
                if st.session_state.confirm_delete == sid:
                    st.warning(f"Delete **{label}**?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, delete", key=f"confirm-{sid}", type="primary"):
                            delete_session(sid)
                            if st.session_state.session_id == sid:
                                st.session_state.session_id = None
                                st.session_state.messages = []
                            st.session_state.confirm_delete = None
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"cancel-{sid}"):
                            st.session_state.confirm_delete = None
                            st.rerun()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

col1, col2 = st.columns([5, 1])
with col1:
    st.title("Multi-LLM Chat")
with col2:
    acc = PROVIDER_COLORS.get(st.session_state.provider, "#4285F4")
    st.markdown(
        f"<div style='padding-top:18px;text-align:right;font-size:0.82rem;"
        f"color:{acc};font-weight:600'>{st.session_state.provider} · "
        f"<span style='font-weight:400;color:#5a6178'>{st.session_state.model_name}</span></div>",
        unsafe_allow_html=True,
    )

# Empty state
if not st.session_state.messages:
    st.markdown(
        "<div style='text-align:center;padding:80px 0 40px;color:#4a5168'>"
        "<div style='font-size:3rem'>💬</div>"
        "<div style='font-size:1.1rem;font-weight:600;color:#5a6178;margin-top:12px'>"
        "Start a new conversation</div>"
        "<div style='font-size:0.88rem;margin-top:6px'>Type a message below to begin</div>"
        "</div>",
        unsafe_allow_html=True,
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Message the AI…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    outgoing_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    with st.chat_message("assistant"):
        if use_streaming:
            placeholder = st.empty()
            collected = ""
            try:
                with requests.post(
                    f"{config.API_URL}/chat/stream",
                    json={
                        "provider": st.session_state.provider,
                        "model_name": st.session_state.model_name,
                        "messages": outgoing_messages,
                        "session_id": st.session_state.session_id,
                    },
                    stream=True, timeout=120,
                ) as response:
                    st.session_state.session_id = response.headers.get(
                        "X-Session-Id", st.session_state.session_id
                    )
                    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                        if chunk:
                            collected += chunk
                            placeholder.markdown(collected)
                answer = collected
            except requests.exceptions.RequestException as e:
                answer = f"⚠️ Connection error: {e}"
                placeholder.markdown(answer)
        else:
            with st.spinner("Thinking…"):
                ok, response_data = api_call(
                    "post", f"{config.API_URL}/chat",
                    json={
                        "provider": st.session_state.provider,
                        "model_name": st.session_state.model_name,
                        "messages": outgoing_messages,
                        "session_id": st.session_state.session_id,
                    },
                )
            if ok:
                answer = response_data["message"]
                st.session_state.session_id = response_data.get("session_id", st.session_state.session_id)
            else:
                answer = f"⚠️ {response_data.get('message', 'Something went wrong.')}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})