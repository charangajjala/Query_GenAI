import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = "http://localhost:8000/query"

st.title("Generative AI Workflow UI")

# Sidebar for Configuration
st.sidebar.header("Configuration")
recursion_limit = st.sidebar.number_input("Recursion Limit", min_value=1, value=100)
thread_id = st.sidebar.text_input("Thread ID", value="1")

# Query Input Section
st.header("Enter Your Query")
query = st.text_area("Query", "Type your question here...")

# Submit Button
if st.button("Run Query"):
    with st.spinner("Processing your query..."):
        try:
            response = requests.post(
                API_URL,
                json={"query": query, "config": {"thread_id": thread_id, "recursion_limit": recursion_limit}},
            )
            if response.status_code == 200:
                data = response.json()
                st.success("Query Processed Successfully!")
                st.write(f"Answer: {data.get('answer', 'No answer returned')}")
                if data.get("chart"):
                    st.image(data["chart"], caption="Generated Chart")
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"An error occurred: {e}")

# (Optional) Display Workflow Graph
if st.checkbox("Show Workflow Graph"):
    st.write("Workflow Graph visualization can go here if supported.")

# (Optional) Logs or Debugging Info
if st.checkbox("Show Logs"):
    st.text("Logs or debug information can be displayed here.")
