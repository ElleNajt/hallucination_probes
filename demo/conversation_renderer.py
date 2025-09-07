"""
Simple conversation builder for multi-turn conversations.
Supports manual turn building and JSON copy-paste.
"""

import streamlit as st
import json
from typing import List, Dict, Any, Optional
import uuid
import json
import os

def conversation_builder_ui(probe_service=None, probe_id=None, repo_id=None, threshold=0.5, max_tokens=512, temperature=0.7) -> tuple[str, List[Dict[str, str]]]:
    """
    Create a UI for building multi-turn conversations.
    Returns: (input_method, list_of_messages)
    """
    # Input method selection
    # input_method = st.radio(
    #     "Choose interaction mode:",
    #     ["Chat with Model", "Build turn-by-turn", "Paste JSON"],
    #     horizontal=True
    # )
    input_method = "Chat with Model"
    
    messages = []
    
    if input_method == "Chat with Model":
        messages = chat_with_model(probe_service, probe_id, repo_id, threshold, max_tokens, temperature)
    elif input_method == "Build turn-by-turn":
        messages = build_conversation_manually()
    else:  # Paste JSON
        messages = import_json_conversation()
    
    return input_method, messages

def build_conversation_manually() -> List[Dict[str, str]]:
    """Build conversation turn by turn."""
    
    # Initialize session state for messages with default turns
    if "conversation_messages" not in st.session_state:
        st.session_state.conversation_messages = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": ""}
        ]
    
    st.subheader("Build Conversation")
    
    # Plus/Minus controls
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("➕ Add Turn"):
            # Determine next role (alternate between user and assistant)
            last_role = st.session_state.conversation_messages[-1]["role"] if st.session_state.conversation_messages else "assistant"
            next_role = "assistant" if last_role == "user" else "user"
            st.session_state.conversation_messages.append({
                "role": next_role,
                "content": ""
            })
            st.rerun()
    
    with col2:
        if st.button("➖ Remove Turn"):
            if len(st.session_state.conversation_messages) > 2:  # Keep at least 2 turns
                st.session_state.conversation_messages.pop()
                st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All"):
            st.session_state.conversation_messages = [
                {"role": "user", "content": ""},
                {"role": "assistant", "content": ""}
            ]
            st.rerun()
    
    # Display and edit turns
    for i, msg in enumerate(st.session_state.conversation_messages):
        role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}
        emoji = role_emoji.get(msg["role"], "💬")
        
        st.markdown(f"**{emoji} {msg['role'].title()}:**")
        
        # Text area for content
        new_content = st.text_area(
            f"Content for turn {i+1}",
            value=msg["content"],
            height=80,
            key=f"turn_content_{i}",
            label_visibility="collapsed"
        )
        
        # Update content if changed
        if new_content != msg["content"]:
            st.session_state.conversation_messages[i]["content"] = new_content
        
        if i < len(st.session_state.conversation_messages) - 1:
            st.divider()
    
    # Export current conversation as JSON
    if st.button("📋 Export JSON"):
        json_str = json.dumps(st.session_state.conversation_messages, indent=2)
        st.code(json_str, language="json")
    
    return st.session_state.conversation_messages

def import_json_conversation() -> List[Dict[str, str]]:
    """Import conversation from JSON."""
    
    st.subheader("Paste JSON Conversation")
    
    # Paste JSON directly
    json_text = st.text_area(
        "Paste JSON here:",
        placeholder='''[
  {"role": "user", "content": "Hello!"},
  {"role": "assistant", "content": "Hi there! How can I help you?"},
  {"role": "user", "content": "What's the weather like?"}
]''',
        height=200
    )
    
    messages = []
    
    try:
        if json_text.strip():
            messages = json.loads(json_text)
            
            # Validate format
            for msg in messages:
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    st.error("Invalid JSON format. Each message should have 'role' and 'content' fields.")
                    return []
            
            st.success(f"✅ Loaded {len(messages)} messages")
            
            # Preview the conversation
            st.subheader("Preview:")
            for i, msg in enumerate(messages):
                role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}
                emoji = role_emoji.get(msg["role"], "💬")
                st.markdown(f"**{emoji} {msg['role'].title()}:** {msg['content']}")
                
                if i < len(messages) - 1:
                    st.divider()
        
    except json.JSONDecodeError as e:
        if json_text.strip():
            st.error(f"Invalid JSON format: {e}")
    except Exception as e:
        st.error(f"Error processing JSON: {e}")
    
    return messages

def chat_with_model(probe_service, probe_id: str, repo_id: Optional[str], threshold: float, max_tokens: int, temperature: float) -> List[Dict[str, str]]:
    """Interactive chat with the model."""
    
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Get current model name
    try:
        current_config = probe_service.get_current_config.remote()
        model_name = current_config.get('model_name', 'Unknown Model')
        # Extract just the model name part for display
        model_display_name = model_name.split('/')[-1] if '/' in model_name else model_name
    except:
        model_display_name = "Model"
    
    # Chat container with custom styling
    st.markdown("""
    <style>
    /* Apply max-width to the main block container in chat mode */
    .main .block-container {
        max-width: 1200px !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .chat-messages {
        background-color: #f7f7f7;
        border-radius: 10px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
        margin-bottom: 10px;
        width: 100%;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 10px 0;
        margin-left: auto;
        max-width: 70%;
        width: fit-content;
        text-align: left;
    }
    .assistant-message {
        background-color: #e8e8e8;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 10px 0;
        margin-right: auto;
        max-width: 70%;
        width: fit-content;
    }
    .message-header {
        font-size: 0.8em;
        color: #666;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .message-wrapper-user {
        display: flex;
        justify-content: flex-end;
    }
    .message-wrapper-assistant {
        display: flex;
        justify-content: flex-start;
    }
    /* Token hover effect */
    .token-hover:hover {
        text-decoration: underline;
    }
    .token-hover:hover::after {
        content: "Probe probability: " attr(data-prob);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background-color: black;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        white-space: nowrap;
        z-index: 1000;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add chat title
    st.markdown(f"##### Model Chat ({model_display_name})")
    
    # Create the chat messages container
    chat_html = '<div class="chat-messages">'
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            chat_html += f'<div class="message-wrapper-user"><div class="user-message"><div class="message-header">User</div>{msg["content"]}</div></div>'
        else:
            # For assistant messages, show with hallucination highlighting if available
            if "html_content" in msg:
                chat_html += f'<div class="message-wrapper-assistant"><div class="assistant-message"><div class="message-header">Assistant</div>{msg["html_content"]}</div></div>'
            else:
                chat_html += f'<div class="message-wrapper-assistant"><div class="assistant-message"><div class="message-header">Assistant</div>{msg["content"]}</div></div>'
    chat_html += '</div>'
    
    # Display chat messages
    st.markdown(chat_html, unsafe_allow_html=True)
    
    # Input area with form to handle clearing
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input("Type your message:", key="chat_input", label_visibility="collapsed", 
                                      placeholder="Type your message here...")
        with col2:
            send_button = st.form_submit_button("Send", type="primary", use_container_width=True)
    
    # Controls area below input - with fixed widths
    controls_col1, controls_col2, controls_col3, spacer = st.columns([1.2, 1.5, 1.5, 4])
    
    with controls_col1:
        if st.button("Clear Chat", type="secondary", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    with controls_col2:
        # Update temperature in session state
        if "chat_temperature" not in st.session_state:
            st.session_state.chat_temperature = temperature
        new_temp = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.chat_temperature,
            step=0.1,
            key="temp_slider",
            help="Controls randomness"
        )
        st.session_state.chat_temperature = new_temp
    
    with controls_col3:
        # Update max tokens in session state
        if "chat_max_tokens" not in st.session_state:
            st.session_state.chat_max_tokens = max_tokens
        new_max_tokens = st.number_input(
            "Max Tokens",
            min_value=10,
            max_value=2048,
            value=st.session_state.chat_max_tokens,
            step=10,
            key="max_tokens_input",
            help="Max tokens to generate"
        )
        st.session_state.chat_max_tokens = new_max_tokens
    
    # Handle sending message
    if send_button and user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Generate response with probe using updated parameters
        if probe_service:
            with st.spinner("Generating response..."):
                try:
                    # Check if probe_id is provided
                    if not probe_id:
                        st.warning("⚠️ Please enter a Probe ID before sending messages.")
                        return
                    
                    result = probe_service.generate_with_probe.remote(
                        st.session_state.chat_history,
                        probe_id,
                        repo_id,
                        threshold,
                        st.session_state.chat_max_tokens,
                        st.session_state.chat_temperature
                    )

                    if "error" in result:
                        st.error(f"Generation failed: {result['error']}")
                    else:
                        # Use returned tokens and text
                        response_tokens = result["generated_tokens"]
                        generated_text = result["generated_text"]
                        response_probs = result["probe_probs"]

                        print(f"Response probs:")
                        for tok, prob in zip(response_tokens, response_probs):
                            print(f"{tok} ({prob:.4f}) ", end="")
                        
                        # Calculate predictions based on threshold
                        response_predictions = [1 if p > threshold else 0 for p in response_probs]
                        
                        # Create highlighted HTML for the response
                        html_content = create_highlighted_response(
                            response_tokens,
                            response_probs,
                            response_predictions,
                            threshold
                        )
                        
                        # Add assistant response to history
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": generated_text,
                            "html_content": html_content,
                            "token_ids": result["generated_token_ids"],
                            "probe_probs": response_probs
                        })
                        
                        # Rerun to update display
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error generating response: {e}")
        else:
            st.error("Probe service not connected")
    
    return st.session_state.chat_history

def create_highlighted_response(tokens: List[str], probabilities: List[float], predictions: List[int], threshold: float = 0.3) -> str:
    """Create HTML with highlighted tokens based on hallucination probabilities."""
    html_parts = []
    
    # Join all tokens to handle bold text across token boundaries
    full_text = ""
    token_boundaries = []  # Track where each token starts and ends
    
    for token in tokens:
        # Clean up token display
        display_token = token.replace('▁', ' ').replace('Ġ', ' ')
        if display_token.startswith('##'):
            display_token = display_token[2:]
        
        # Handle Unicode characters that represent newlines
        display_token = display_token.replace('\u010a', '\n')  # Ċ -> newline
        display_token = display_token.replace('\u0120', ' ')   # Ġ -> space (if not already handled)
        
        # Also handle escaped Unicode sequences that might come from JSON
        if '\\u0120' in display_token:
            display_token = display_token.replace('\\u0120', ' ')
        if '\\u010a' in display_token:
            display_token = display_token.replace('\\u010a', '\n')
        
        token_boundaries.append((len(full_text), len(full_text) + len(display_token)))
        full_text += display_token
    
    is_bold = False
    for token_idx, (token, prob) in enumerate(zip(tokens, probabilities)):
        # Clean up token display (same as before)
        display_token = token.replace('▁', ' ').replace('Ġ', ' ')
        if display_token.startswith('##'):
            display_token = display_token[2:]
        display_token = display_token.replace('\u010a', '\n')
        display_token = display_token.replace('\u0120', ' ')
        
        # Also handle escaped Unicode sequences that might come from JSON
        if '\\u0120' in display_token:
            display_token = display_token.replace('\\u0120', ' ')
        if '\\u010a' in display_token:
            display_token = display_token.replace('\\u010a', '\n')

        if "**" in display_token:
            # Skip tokens that are just ** markers
            is_bold = False if is_bold else True
            display_token = display_token.replace("**", "")
            if not display_token:
                continue
        elif display_token == '<|eot_id|>':
            # Skip eos token
            continue
        
        # Color based on hallucination probability
        if prob > threshold:
            color = f"rgba(255, 0, 0, {0.15 + 0.4 * (prob - threshold) / (1 - threshold)})"
        else:
            color = "transparent"
        
        # Create a span for the entire token with hover tooltip
        token_html = f'<span class="token-hover" style="background: {color}; cursor: pointer; position: relative;" ' \
                     f'data-prob="{prob:.3f}">'
        
        # Process each character in the token
        for char in display_token:
            
            if char == '\n':
                # For newlines, just add a line break with no visual indicator
                token_html += '<br>'
            else:
                # Escape HTML characters
                # escaped_char = char.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                escaped_char = char
                if is_bold:
                    token_html += f'<strong>{escaped_char}</strong>'
                else:
                    token_html += escaped_char
            
            # char_index += 1
        
        token_html += '</span>'
        html_parts.append(token_html)
    
    return "".join(html_parts)

def render_streaming_conversation(chat_history, streaming_delay=0.05):
    """Render conversation with simulated token streaming animation."""
    import time
    
    # Extract assistant message data
    if len(chat_history) < 2:
        st.error("Need at least user and assistant messages")
        return
    
    user_msg = chat_history[0]
    assistant_msg = chat_history[1]
    
    # Get tokens and probabilities
    tokens = assistant_msg.get("generated_tokens", [])
    probabilities = assistant_msg.get("probe_probs", [])
    
    if not tokens or not probabilities:
        st.error("No token data available")
        return
    
    # Add CSS styling (same as render_debug_conversation)
    st.markdown("""
    <style>
    /* Apply max-width to the main block container in chat mode */
    .main .block-container {
        max-width: 1200px !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .streaming-messages {
        background-color: #f7f7f7;
        border-radius: 10px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
        margin-bottom: 10px;
        width: 100%;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 10px 0;
        margin-left: auto;
        max-width: 70%;
        width: fit-content;
        text-align: left;
    }
    .assistant-message {
        background-color: #e8e8e8;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 10px 0;
        margin-right: auto;
        max-width: 70%;
        width: fit-content;
    }
    .message-header {
        font-size: 0.8em;
        color: #666;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .message-wrapper-user {
        display: flex;
        justify-content: flex-end;
    }
    .message-wrapper-assistant {
        display: flex;
        justify-content: flex-start;
    }
    /* Token hover effect */
    .token-hover:hover {
        text-decoration: underline;
    }
    .token-hover:hover::after {
        content: "Probe probability: " attr(data-prob);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background-color: black;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        white-space: nowrap;
        z-index: 1000;
        margin-bottom: 2px;
    }
    /* Typing cursor animation */
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0; }
        100% { opacity: 1; }
    }
    .typing-cursor {
        display: inline-block;
        width: 2px;
        height: 1.2em;
        background-color: #333;
        animation: blink 1s infinite;
        vertical-align: text-bottom;
        margin-left: 2px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.markdown("##### Streaming Token Animation")
    
    # Create containers
    chat_container = st.container()
    progress_container = st.container()
    
    # Show user message immediately
    with chat_container:
        user_html = f'''
        <div class="streaming-messages">
            <div class="message-wrapper-user">
                <div class="user-message">
                    <div class="message-header">User</div>
                    {user_msg["content"]}
                </div>
            </div>
            <div class="message-wrapper-assistant">
                <div class="assistant-message">
                    <div class="message-header">Assistant</div>
                    <div id="assistant-content"></div>
                </div>
            </div>
        </div>
        '''
        message_placeholder = st.empty()
        message_placeholder.markdown(user_html, unsafe_allow_html=True)
    
    # Progress bar
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    # Generate tokens progressively
    threshold = 0.2
    for i in range(len(tokens)):
        # Update progress
        progress = (i + 1) / len(tokens)
        progress_bar.progress(progress)
        status_text.text(f"Generating token {i+1} of {len(tokens)}...")
        
        # Generate HTML for tokens up to current position
        current_tokens = tokens[:i+1]
        current_probs = probabilities[:i+1]
        predictions = [1 if p > threshold else 0 for p in current_probs]
        
        # Create HTML content for current tokens
        html_content = create_highlighted_response(
            current_tokens,
            current_probs,
            predictions,
            threshold
        )
        
        # Add typing cursor if not at the end
        if i < len(tokens) - 1:
            html_content += '<span class="typing-cursor"></span>'
        
        # Update the display
        updated_html = f'''
        <div class="streaming-messages">
            <div class="message-wrapper-user">
                <div class="user-message">
                    <div class="message-header">User</div>
                    {user_msg["content"]}
                </div>
            </div>
            <div class="message-wrapper-assistant">
                <div class="assistant-message">
                    <div class="message-header">Assistant</div>
                    {html_content}
                </div>
            </div>
        </div>
        '''
        message_placeholder.markdown(updated_html, unsafe_allow_html=True)
        
        # Sleep to simulate streaming delay
        time.sleep(streaming_delay)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Show completion message
    st.success("✅ Generation complete!")

def render_debug_conversation(chat_history):
    """Debug function to render conversation with hardcoded values."""
    
    threshold = 0.30
    
    # Generate HTML content for assistant message
    assistant_msg = chat_history[1]
    response_predictions = [1 if p > threshold else 0 for p in assistant_msg["probe_probs"]]
    html_content = create_highlighted_response(
        assistant_msg["generated_tokens"],
        assistant_msg["probe_probs"],
        response_predictions,
        threshold
    )
    chat_history[1]["html_content"] = html_content
    
    # Chat container with custom styling (exact same as chat_with_model)
    st.markdown("""
    <style>
    /* Apply max-width to the main block container in chat mode */
    .main .block-container {
        max-width: 1200px !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .chat-messages {
        background-color: #f7f7f7;
        border-radius: 10px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
        margin-bottom: 10px;
        width: 100%;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 10px 0;
        margin-left: auto;
        max-width: 70%;
        width: fit-content;
        text-align: left;
    }
    .assistant-message {
        background-color: #e8e8e8;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 10px 0;
        margin-right: auto;
        max-width: 70%;
        width: fit-content;
    }
    .message-header {
        font-size: 0.8em;
        color: #666;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .message-wrapper-user {
        display: flex;
        justify-content: flex-end;
    }
    .message-wrapper-assistant {
        display: flex;
        justify-content: flex-start;
    }
    /* Token hover effect */
    .token-hover:hover {
        text-decoration: underline;
    }
    .token-hover:hover::after {
        content: "Probe probability: " attr(data-prob);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background-color: black;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        white-space: nowrap;
        z-index: 1000;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add chat title
    st.markdown(f"##### Debug Chat Display")
    
    # Create the chat messages container (exact same as chat_with_model)
    chat_html = '<div class="chat-messages">'
    for msg in chat_history:
        if msg["role"] == "user":
            chat_html += f'<div class="message-wrapper-user"><div class="user-message"><div class="message-header">User</div>{msg["content"]}</div></div>'
        else:
            # For assistant messages, show with hallucination highlighting if available
            if "html_content" in msg:
                chat_html += f'<div class="message-wrapper-assistant"><div class="assistant-message"><div class="message-header">Assistant</div>{msg["html_content"]}</div></div>'
            else:
                chat_html += f'<div class="message-wrapper-assistant"><div class="assistant-message"><div class="message-header">Assistant</div>{msg["content"]}</div></div>'
    chat_html += '</div>'
    
    # Display chat messages
    st.markdown(chat_html, unsafe_allow_html=True)
    
    # Show debug information
    st.markdown("---")
    st.markdown("### Debug Information")
    
    # Token analysis table
    st.markdown("**Token Analysis:**")
    token_data = []
    for i, (token, prob) in enumerate(zip(assistant_msg["generated_tokens"], assistant_msg["probe_probs"])):
        token_data.append({
            "Index": i,
            "Token": token,
            "Display": token.replace('Ġ', ' '),
            "Probability": f"{prob:.4f}",
            "Hallucination": "Yes" if prob > threshold else "No"
        })
    st.dataframe(token_data)
    
    # Show the HTML content for debugging
    with st.expander("Generated HTML Content"):
        st.code(html_content, language="html")