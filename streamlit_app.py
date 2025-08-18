import streamlit as st
import requests
import uuid
import pandas as pd
import plotly.express as px

API_BASE_URL = "http://localhost:8003"

st.set_page_config(page_title="Database analysis assistant")
# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.title("LLM driven analysis of your database")

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

chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display chart if present
            if message.get("chart"):
                render_chart(message["chart"])

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
                        chart_data = result.get("chart_data")
                        if chart_data:
                            message_data["chart"] = chart_data
                            render_chart(chart_data)
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
