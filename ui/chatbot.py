"""
Simple Chatbot UI for SAP Agent Testing.

Run with: streamlit run ui/chatbot.py
"""
import streamlit as st
import requests
import os
from datetime import datetime

# Configuration - Use environment variable for Docker, fallback to localhost
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
SAP_API_URL = BASE_URL + "/sap/tools"

st.set_page_config(
    page_title="SAP Assistant Chatbot",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better chat UI with loading animation
st.markdown("""
<style>
    .stTextInput > div > div > input {
        font-size: 16px;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .bot-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    .message-time {
        font-size: 0.75rem;
        color: #666;
        margin-top: 0.5rem;
    }
    
    /* Loading animation */
    .loading-container {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 20px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin: 10px 0;
    }
    .loading-dots {
        display: flex;
        gap: 8px;
    }
    .loading-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background-color: #1f77b4;
        animation: bounce 1.4s infinite ease-in-out both;
    }
    .loading-dot:nth-child(1) {
        animation-delay: -0.32s;
    }
    .loading-dot:nth-child(2) {
        animation-delay: -0.16s;
    }
    @keyframes bounce {
        0%, 80%, 100% { 
            transform: scale(0);
            opacity: 0.5;
        }
        40% { 
            transform: scale(1);
            opacity: 1;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []
    # Welcome message
    st.session_state.messages.append({
        "role": "assistant",
        "content": "👋 Hello! I'm your SAP Assistant. Ask me anything about your SAP systems!\n\nFor example:\n• Get table schema for MAKT from D2A\n• Show source code for ZCL_JIRA_ISSUES from D2A\n• Get subscription details for INTVG1232 from D2A",
        "timestamp": datetime.now().strftime("%H:%M")
    })

# Header
st.title("🤖 SAP Assistant")
st.markdown("Ask questions about your SAP systems in natural language")

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This chatbot uses AI to help you query SAP systems.
    
    **What you can ask:**
    - Table schemas
    - Source code
    - Service items
    - Subscription details
    - Application logs
    - Service metadata
    
    **Available Systems:**
    - D2A (Development)
    - QHA (QA)
    - RHA (Pre-Production)
    - SHA (Sandbox)
    """)
    
    st.markdown("---")
    
    # API Status
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        if response.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ API Offline")
    
    st.markdown("---")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        role_icon = "👤" if message["role"] == "user" else "🤖"
        role_name = "You" if message["role"] == "user" else "SAP Assistant"
        
        with st.chat_message(message["role"]):
            st.markdown(f"**{role_icon} {role_name}**")
            st.markdown(message["content"])
            st.caption(message["timestamp"])

# Chat input
prompt = st.chat_input("Ask me anything about SAP...")

if prompt:
    # Add user message to chat
    timestamp = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "timestamp": timestamp
    })
    
    # Display user message immediately
    with chat_container:
        with st.chat_message("user"):
            st.markdown(f"**👤 You**")
            st.markdown(prompt)
            st.caption(timestamp)
    
    # Show loading animation
    with chat_container:
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st.markdown("""
            <div class="loading-container">
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
                <span style="color: #666; font-size: 14px;">🤖 SAP Assistant is thinking...</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Get bot response
    try:
        # Call the SAP API
        response = requests.get(
            SAP_API_URL,
            params={"user_query": prompt},
            timeout=60
        )
        
        timestamp = datetime.now().strftime("%H:%M")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                bot_message = result.get("response", "No response received")
            else:
                error_msg = result.get("error", "Unknown error occurred")
                bot_message = f"❌ Sorry, I encountered an error:\n\n{error_msg}"
        else:
            # Handle different error status codes
            try:
                error_detail = response.json().get("detail", response.text)
            except:
                error_detail = response.text
            
            bot_message = f"❌ API Error ({response.status_code}):\n\n{error_detail}"
        
        # Clear loading animation
        loading_placeholder.empty()
        
        # Add bot response to chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_message,
            "timestamp": timestamp
        })
    
    except requests.exceptions.Timeout:
        timestamp = datetime.now().strftime("%H:%M")
        bot_message = "⏱️ Request timed out. The query might be taking too long. Please try again or simplify your question."
        
        loading_placeholder.empty()
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_message,
            "timestamp": timestamp
        })
    
    except Exception as e:
        timestamp = datetime.now().strftime("%H:%M")
        bot_message = f"❌ Error: {str(e)}"
        
        loading_placeholder.empty()
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_message,
            "timestamp": timestamp
        })
    
    # Force rerun to clear the input and show the response
    st.rerun()

# Footer
st.markdown("---")
st.caption("💡 Tip: Be specific with system names (D2A, QHA, etc.) and object names for best results")
