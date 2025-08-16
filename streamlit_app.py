import streamlit as st
import requests
import json
from typing import Optional
import uuid
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Configure the page
st.set_page_config(
    page_title="Database Analysis Chat",
    page_icon="🗄️",
    layout="wide"
)

# API configuration
API_BASE_URL = "http://localhost:8003"  # Update this if your API runs on a different port

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# App header
st.title("🗄️ Database Analysis Chat")
st.markdown("Chat with your databases using natural language queries")

# Sidebar for settings and info
with st.sidebar:
    st.header("⚙️ Settings")

    # API endpoint configuration
    api_url = st.text_input(
        "API Endpoint",
        value=API_BASE_URL,
        help="FastAPI server endpoint"
    )

    # Session management
    st.divider()
    st.subheader("Session Management")
    st.text(f"Session ID: {st.session_state.session_id[:8]}...")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Chat", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    with col2:
        if st.button("New Session", type="secondary", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            # Try to clear the session on the backend
            try:
                requests.delete(f"{api_url}/chat/{st.session_state.session_id}")
            except:
                pass
            st.rerun()

    # Info section
    st.divider()
    st.subheader("ℹ️ How to Use")
    st.markdown("""
    - Ask questions about your databases in natural language
    - The AI will query the appropriate database and return results
    - Your conversation history is maintained during the session

    **Example queries:**
    - "Show me all customers from the USA"
    - "What are the top 5 best-selling products?"
    - "List all tables in the database"
    - "How many orders were placed last month?"

    **Chart queries:**
    - "Show me the top 5 genres by track count in a bar chart"
    - "Display monthly sales trends as a line chart"
    - "What percentage of tracks are in each media type? (pie chart)"
    """)

    # Connection status
    st.divider()
    st.subheader("🔌 Connection Status")
    try:
        response = requests.get(f"{api_url}/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ Connected to API")
        else:
            st.error("❌ API returned error")
    except requests.exceptions.RequestException:
        print("Connection error", api_url)
        st.error("❌ Cannot connect to API")
        st.info(f"Make sure the FastAPI server is running at {api_url}")

# Function to render charts using Plotly
def render_chart(chart_config):
    """Render a chart based on the configuration from the API."""
    try:
        chart_type = chart_config.get("type", "bar")
        title = chart_config.get("title", "Chart")
        data = chart_config.get("data", {})
        options = chart_config.get("options", {})

        labels = data.get("labels", [])
        datasets = data.get("datasets", [])

        if not labels or not datasets:
            st.warning("No data available for chart")
            return

        # Create DataFrame for Plotly
        df_data = {"labels": labels}
        for dataset in datasets:
            df_data[dataset.get("label", "Data")] = dataset.get("data", [])
        df = pd.DataFrame(df_data)

        # Create chart based on type
        if chart_type == "bar":
            fig = px.bar(
                df,
                x="labels",
                y=df.columns[1],
                title=title,
                labels={"labels": options.get("scales", {}).get("x", {}).get("title", {}).get("text", ""),
                        df.columns[1]: options.get("scales", {}).get("y", {}).get("title", {}).get("text", "")}
            )
        elif chart_type == "line":
            fig = px.line(
                df,
                x="labels",
                y=df.columns[1:],
                title=title,
                labels={"labels": options.get("scales", {}).get("x", {}).get("title", {}).get("text", ""),
                        "value": options.get("scales", {}).get("y", {}).get("title", {}).get("text", "")}
            )
        elif chart_type == "pie":
            fig = px.pie(
                values=datasets[0].get("data", []),
                names=labels,
                title=title
            )
        elif chart_type == "scatter":
            fig = px.scatter(
                df,
                x="labels",
                y=df.columns[1],
                title=title,
                labels={"labels": options.get("scales", {}).get("x", {}).get("title", {}).get("text", ""),
                        df.columns[1]: options.get("scales", {}).get("y", {}).get("title", {}).get("text", "")}
            )
        elif chart_type == "area":
            fig = px.area(
                df,
                x="labels",
                y=df.columns[1:],
                title=title,
                labels={"labels": options.get("scales", {}).get("x", {}).get("title", {}).get("text", ""),
                        "value": options.get("scales", {}).get("y", {}).get("title", {}).get("text", "")}
            )
        else:
            # Fallback to bar chart
            fig = px.bar(
                df,
                x="labels",
                y=df.columns[1],
                title=title
            )

        # Update layout
        fig.update_layout(
            xaxis_title=options.get("scales", {}).get("x", {}).get("title", {}).get("text", ""),
            yaxis_title=options.get("scales", {}).get("y", {}).get("title", {}).get("text", ""),
            showlegend=len(datasets) > 1,
            height=400
        )

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error rendering chart: {str(e)}")
        st.json(chart_config)  # Show raw data as fallback

# Main chat interface
chat_container = st.container()

# Display chat messages
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display chart if present
            if message.get("chart"):
                render_chart(message["chart"])

# Chat input
if prompt := st.chat_input("Ask a question about your database..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

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
                    f"{api_url}/chat",
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=60  # 60 second timeout for complex queries
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
                        # Display successful response
                        assistant_response = result.get("response", "No response received")
                        st.markdown(assistant_response)

                        # Display chart if present
                        chart_data = result.get("chart")
                        if chart_data:
                            render_chart(chart_data)

                        # Store message with chart data
                        message_data = {
                            "role": "assistant",
                            "content": assistant_response
                        }
                        if chart_data:
                            message_data["chart"] = chart_data

                        st.session_state.messages.append(message_data)

                        # Update session ID if provided
                        if result.get("session_id"):
                            st.session_state.session_id = result["session_id"]
                else:
                    error_message = f"❌ API Error: {response.status_code} - {response.text}"
                    st.error(error_message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })

            except requests.exceptions.Timeout:
                error_message = "⏱️ Request timed out. The query might be too complex."
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })

            except requests.exceptions.ConnectionError:
                error_message = "❌ Cannot connect to the API server. Please check if it's running."
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })

            except Exception as e:
                error_message = f"❌ Unexpected error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })

# Footer
st.divider()
st.caption("💡 Tip: You can ask questions about database schemas, run queries, and analyze data using natural language.")
