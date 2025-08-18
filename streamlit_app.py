import streamlit as st
import requests
import uuid

API_BASE_URL = "http://localhost:8003"

st.set_page_config(page_title="Database analysis assistant")
# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.title("LLM driven analysis of your database")

chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your database..."):
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response with spinner
    with st.chat_message("assistant"):
        with st.spinner("Analyzing database..."):
            try:
                # Prepare the request
                request_data = {
                    "query": prompt,
                    "session_id": st.session_state.session_id
                }

                # Make API request
                response = requests.post(
                    f"{API_BASE_URL}/chat",
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()

                    if result.get("error"):
                        # Display error message
                        error_message = f"❌ Error: {result['error']}"
                        st.error(error_message)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_message
                        })
                    else:
                        assistant_response = result.get("response", "No response received")
                        st.markdown(assistant_response)
                        message_data = {
                            "role": "assistant",
                            "content": assistant_response
                        }
                        st.session_state.messages.append(message_data)

                        if result.get("session_id"):
                            st.session_state.session_id = result.get("session_id")
                else:
                    error_message = f"❌ API Error: {response.status_code} - {response.text}"
                    st.error(error_message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })

            except requests.exceptions.Timeout:
                error_message = "Request timed out. The query might be too complex."
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })

            except Exception as e:
                error_message = f"Unexpected error {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })
