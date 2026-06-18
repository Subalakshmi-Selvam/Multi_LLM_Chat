import streamlit as st
import requests
from chatbot_ui.core.config import config

st.set_page_config(page_title="Multi-LLM Chat", page_icon="💬", layout="wide")

PROVIDER_MODELS = {
    "Groq": ["llama-3.3-70b-versatile"],
    "Google": ["gemini-2.5-flash"],
}


def api_call(method, url, **kwargs):
    """Call the API and surface failures as an inline error rather than a stack trace."""
    try:
        response = getattr(requests, method)(url, **kwargs)
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = {"message": "Invalid response format from server"}

        if response.ok:
            return True, response_data
        return False, response_data

    except requests.exceptions.ConnectionError:
        return False, {"message": "Could not reach the API. Is it running?"}
    except requests.exceptions.Timeout:
        return False, {"message": "The request timed out. Please try again."}
    except Exception as e:  # noqa: BLE001
        return False, {"message": str(e)}


def load_sessions():
    ok, data = api_call("get", f"{config.API_URL}/sessions")
    return data if ok else []


def load_messages(session_id):
    ok, data = api_call("get", f"{config.API_URL}/sessions/{session_id}/messages")
    return data if ok else []


# ---------------------------------------------------------------------------
# Sidebar: provider/model picker, system prompt, chat history list
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Settings")

    provider = st.selectbox("Provider", list(PROVIDER_MODELS.keys()))
    model_name = st.selectbox("Model", PROVIDER_MODELS[provider])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    system_prompt = st.text_area(
        "System prompt",
        value="You are a helpful assistant.",
        height=80,
    )
    use_streaming = st.toggle("Stream responses", value=True)

    st.session_state.provider = provider
    st.session_state.model_name = model_name

    st.divider()
    st.subheader("Chats")

    if st.button("➕ New chat", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    sessions = load_sessions()
    for s in sessions:
        label = s["title"] or "Untitled chat"
        if st.button(label, key=f"session-{s['id']}", use_container_width=True):
            st.session_state.session_id = s["id"]
            history = load_messages(s["id"])
            st.session_state.messages = [
                {"role": m["role"], "content": m["content"]} for m in history
            ]
            st.rerun()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I assist you today?"}
    ]
if "session_id" not in st.session_state:
    st.session_state.session_id = None

st.title("💬 Multi-LLM Chat")
st.caption(f"Talking to **{st.session_state.provider}** / `{st.session_state.model_name}`")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything..."):
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
                    stream=True,
                    timeout=120,
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
            with st.spinner("Thinking..."):
                ok, response_data = api_call(
                    "post",
                    f"{config.API_URL}/chat",
                    json={
                        "provider": st.session_state.provider,
                        "model_name": st.session_state.model_name,
                        "messages": outgoing_messages,
                        "session_id": st.session_state.session_id,
                    },
                )
            if ok:
                answer = response_data["message"]
                st.session_state.session_id = response_data.get(
                    "session_id", st.session_state.session_id
                )
            else:
                answer = f"⚠️ {response_data.get('message', 'Something went wrong.')}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
