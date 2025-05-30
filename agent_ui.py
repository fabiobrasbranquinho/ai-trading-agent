# File: agent_ui.py
import streamlit as st
import google.generativeai as genai
import datetime
import random
import os # Still useful for a potential environment variable fallback

# --- Import functions from your logic file ---
from my_ai_agent_logic import (
    load_data_from_file,
    log_to_file,
    get_help_for_ui,
    get_my_terms_list_text,
    process_ai_query
)

# --- Configuration File Paths (Local Paths) ---
persona_config_filename = "persona_config.json"
help_filename = "persona_help.txt" 
my_terms_filename = "my_trading_terms.json"

# --- Main Streamlit App Logic ---
def main():
    st.set_page_config(page_title="AI Trading Explainer", layout="wide")
    st.title("💬 AI Trading Term Explainer")
    st.caption("Your personal AI assistant for understanding trading and financial concepts.")
    
    # --- Sidebar ---
    with st.sidebar:
        st.header("Controls")
        if st.button("🔄 New Chat / Reset", key="reset_button_sidebar_corrected"):
            if st.session_state.get("agent_initialized", False): 
                # Re-initialize chat session using the template stored in session_state
                st.session_state.chat_session = st.session_state.model.start_chat(
                    history=st.session_state.initial_chat_history_template # Use the template
                )
                st.session_state.display_messages = [] 
                reset_msg_sidebar = "Conversation has been reset!"
                # Add AI's initial greeting back to display
                if st.session_state.chat_session.history and st.session_state.chat_session.history[-1].role == "model":
                    reset_msg_sidebar = st.session_state.chat_session.history[-1].parts[0].text
                st.session_state.display_messages.append({"role": "assistant", "content": reset_msg_sidebar})
                
                if "log_file" in st.session_state: 
                    log_to_file(st.session_state.log_file, "--- User clicked Reset Chat button from sidebar ---")
                    log_to_file(st.session_state.log_file, reset_msg_sidebar, speaker="AI Agent")
                    log_to_file(st.session_state.log_file, "---")
                st.success("Chat reset successfully!") 
                st.rerun()
            else:
                st.warning("Agent not initialized yet. Cannot reset.")
                
        # Inside the 'with st.sidebar:' block
        if st.button("❓ Show Help", key="help_button_sidebar"):
            if st.session_state.get("agent_initialized", False):
                help_text = get_help_for_ui(st.session_state.help_text, st.session_state.log_file)
                st.session_state.display_messages.append({"role": "assistant", "content": help_text})
                st.rerun()
            else:
                st.warning("Agent not initialized yet.")
        
        if st.button("📚 List My Terms", key="my_terms_button_sidebar"):
            if st.session_state.get("agent_initialized", False):
                terms_text_to_display = get_my_terms_list_text(
                    st.session_state.knowledge_base, 
                    st.session_state.log_file
            )
                st.session_state.display_messages.append({
                    "role": "assistant", 
                    "content": terms_text_to_display
                })
                # Log that the button was clicked (optional, as get_my_terms_list_text already logs)
                # log_to_file(st.session_state.log_file, "--- User clicked List My Terms button ---")
                st.rerun()
            else:
                st.warning("Agent not initialized yet.")
        
        if st.button("🎲 Explain Random Term", key="random_term_button_sidebar"):  
            if st.session_state.get("agent_initialized", False):
                log_to_file(st.session_state.log_file, "--- User clicked Explain Random Term button ---")
                if st.session_state.knowledge_base:
                    available_terms = list(st.session_state.knowledge_base.keys())
                    random_term_key = random.choice(available_terms) # random_term_key is lowercase
                    
                    selection_msg = f"Okay, let's talk about: '{random_term_key.title()}'"
                    st.session_state.display_messages.append({"role": "assistant", "content": selection_msg})
                    log_to_file(st.session_state.log_file, selection_msg, speaker="AI Agent")
                    
                    with st.spinner("AI is thinking..."):
                        ai_messages_list = process_ai_query(
                            random_term_key.title(), # Pass title cased for original query if needed by process_ai_query
                            random_term_key,         # Pass lowercase for KB lookup
                            st.session_state.chat_session, 
                            st.session_state.knowledge_base, 
                            st.session_state.log_file,
                            st.session_state.initial_chat_history_template 
                        )
                    for msg_info in ai_messages_list:
                        # Normalize speaker role for st.chat_message
                        role = "assistant" 
                        if "speaker_type" in msg_info:
                            s_type = msg_info["speaker_type"].lower()
                            if "local" in s_type: role = "assistant"
                            elif "llm" in s_type: role = "assistant"
                            elif "system_info" in s_type: role = "assistant"
                            elif "system_error" in s_type: role = "assistant"
                        st.session_state.display_messages.append({"role": role, "content": msg_info["text"]})
                    else:
                        no_terms_msg = "My local knowledge base is empty, so I can't pick a random term."
                        st.session_state.display_messages.append({"role": "assistant", "content": no_terms_msg})
                        log_to_file(st.session_state.log_file, no_terms_msg, speaker="AI Agent")
                        
                    log_to_file(st.session_state.log_file, "---") # Log separator after command action
                    st.rerun()
                else:
                    st.warning("Agent not initialized yet.")
            
        st.markdown("---")

    st.markdown("---") # Main page separator

    # --- Initialization using st.session_state ---
    if "agent_initialized" not in st.session_state:
        st.info("Agent is initializing...")
        api_key_to_use = None

        # ...
        st.session_state.help_text = load_data_from_file(help_filename, file_type="txt") # Or whatever variable you load it into
        if not st.session_state.help_text: # Fallback
            st.warning(f"Help file '{help_filename}' not loaded. Using minimal default.")
            st.session_state.help_text = "Default Help: Ask questions. Type /quit to exit."
        # ...
            
        try: # Try secrets first
            api_key_to_use = st.secrets.get("GOOGLE_API_KEY")
            if api_key_to_use:
                print("API Key loaded from Streamlit Secrets.")
        except Exception: # Broad exception if st.secrets itself is not available/errors
            print("Streamlit Secrets not available or key not found. Trying environment variable.")
            api_key_to_use = None # Ensure it's None if secrets failed

        if not api_key_to_use: # If not found in secrets, try environment variable
            api_key_to_use = os.environ.get("GOOGLE_API_KEY")
            if api_key_to_use:
                print("API Key loaded from Environment Variable.")
            else:
                print("GOOGLE_API_KEY not found as an environment variable either.")
        
        if not api_key_to_use: # If still not found, error out
            st.error("API Key not found in Streamlit Secrets or as GOOGLE_API_KEY environment variable. Please set it up.")
            st.stop()
        
        st.session_state.GOOGLE_API_KEY = api_key_to_use
        
        try:
            genai.configure(api_key=st.session_state.GOOGLE_API_KEY)
            
            st.session_state.model_name_to_use = 'gemini-2.0-flash' # Hardcoded model
            st.session_state.model = genai.GenerativeModel(st.session_state.model_name_to_use)
            
            # Define LOCAL file paths (assuming files are in the same directory as agent_ui.py)
            # These should be defined here or globally at the top of agent_ui.py
            loc_persona_config_filename = "persona_config.json"
            loc_help_filename = "persona_help.txt"
            loc_my_terms_filename = "my_trading_terms.json"

            st.session_state.initial_chat_history_template = load_data_from_file(loc_persona_config_filename, file_type="json")
            if not st.session_state.initial_chat_history_template: 
                st.warning(f"Persona file '{loc_persona_config_filename}' not loaded. Using minimal default.")
                st.session_state.initial_chat_history_template = [{"role": "user", "parts": [{"text": "Basic AI."}]}, {"role": "model", "parts": [{"text": "Hi."}]}]

            st.session_state.help_text_content = load_data_from_file(loc_help_filename, file_type="txt") # Store in different var
            if not st.session_state.help_text_content:
                st.warning(f"Help file '{loc_help_filename}' not loaded. Using minimal default.")
                st.session_state.help_text_content = "Default Help: Ask questions. Type /quit to exit."

            loaded_terms = load_data_from_file(loc_my_terms_filename, file_type="json")
            kb = {}
            if isinstance(loaded_terms, list):
                for item in loaded_terms:
                    if isinstance(item, dict) and "term" in item and "definition" in item:
                        kb[item["term"].lower()] = item["definition"]
            st.session_state.knowledge_base = kb
            
            st.session_state.chat_session = st.session_state.model.start_chat(history=st.session_state.initial_chat_history_template)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.log_file = f"ai_chat_log_streamlit_{timestamp}.txt"
            with open(st.session_state.log_file, "w", encoding="utf-8") as f:
                f.write(f"Chat Log: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Model: {st.session_state.model_name_to_use}\n")
                f.write(f"Persona: {loc_persona_config_filename}\nHelp: {loc_help_filename}\nTerms: {loc_my_terms_filename}\n")
                f.write(f"Loaded {len(st.session_state.knowledge_base)} local terms.\n")
            log_to_file(st.session_state.log_file, "=" * 40)
            if st.session_state.chat_session.history and st.session_state.chat_session.history[-1].role == "model":
                log_to_file(st.session_state.log_file, st.session_state.chat_session.history[-1].parts[0].text, speaker="AI Agent")
                log_to_file(st.session_state.log_file, "=" * 40)
            
            st.session_state.agent_initialized = True
            st.success(f"Agent initialized with {st.session_state.model_name_to_use}!")
            st.rerun()

        except Exception as e:
            st.error(f"Critical error during agent initialization: {e}")
            if "agent_initialized" in st.session_state: del st.session_state.agent_initialized
            st.stop()

    if not st.session_state.get("agent_initialized", False):
        st.info("Agent initialization pending or failed. Please check messages above, console for errors, or ensure API key is correctly set in .streamlit/secrets.toml or as an environment variable.")
        st.stop()

    # Initialize chat display history in session state if not already present
    if "display_messages" not in st.session_state:
        st.session_state.display_messages = []
        current_history_for_display = st.session_state.chat_session.history
        if current_history_for_display and current_history_for_display[-1].role == "model":
            st.session_state.display_messages.append({
                "role": "assistant", 
                "content": current_history_for_display[-1].parts[0].text
            })
        # Fallback if chat_session history is empty but template exists (e.g. after a reset that had an empty template)
        elif st.session_state.initial_chat_history_template and st.session_state.initial_chat_history_template[-1]["role"] == "model":
            st.session_state.display_messages.append({
                "role": "assistant",
                "content": st.session_state.initial_chat_history_template[-1]["parts"][0]["text"]
            })

    # Display chat messages from st.session_state.display_messages
    for msg in st.session_state.display_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- User Input ---
    user_query = st.chat_input("Ask about a trading term or type a command...", key="chat_input_widget_v2") # Changed key to help refresh

    if user_query:
        st.session_state.display_messages.append({"role": "user", "content": user_query})
        log_to_file(st.session_state.log_file, user_query, speaker="User")
        
        user_query_lc = user_query.lower()
        should_rerun_after_processing = True 

        if user_query_lc in ['quit', 'exit']:
            goodbye = "Goodbye! Hope this was helpful."
            st.session_state.display_messages.append({"role": "assistant", "content": goodbye})
            log_to_file(st.session_state.log_file, goodbye, speaker="AI Agent")
            log_to_file(st.session_state.log_file, "---")
            log_to_file(st.session_state.log_file, f"Chat ended: {datetime.datetime.now()}", speaker="System")
            log_to_file(st.session_state.log_file, "=" * 40)
            st.info("Chat session ended. Refresh the page to start a new session.")
            should_rerun_after_processing = False 
        
        elif user_query_lc == '/reset':
            st.session_state.chat_session = st.session_state.model.start_chat(history=st.session_state.initial_chat_history_template)
            st.session_state.display_messages = [] 
            reset_msg = "Conversation reset by user."
            current_history_after_reset = st.session_state.chat_session.history
            if current_history_after_reset and current_history_after_reset[-1].role == "model":
                reset_msg = current_history_after_reset[-1].parts[0].text
            st.session_state.display_messages.append({"role": "assistant", "content": reset_msg})
            log_to_file(st.session_state.log_file, "--- User typed /reset ---")
            log_to_file(st.session_state.log_file, reset_msg, speaker="AI Agent")
            log_to_file(st.session_state.log_file, "---")
        
        elif user_query_lc == '/help':
            help_text_returned = get_help_for_ui(st.session_state.help_text_content, st.session_state.log_file) # Use correct var
            st.session_state.display_messages.append({"role": "assistant", "content": help_text_returned})

        elif user_query_lc == '/my_terms':
            terms_text_returned = get_my_terms_list_text(st.session_state.knowledge_base, st.session_state.log_file)
            st.session_state.display_messages.append({"role": "assistant", "content": terms_text_returned})

        elif user_query_lc == '/random_term':
            log_to_file(st.session_state.log_file, "--- User typed /random_term ---")
            if st.session_state.knowledge_base:
                available_terms = list(st.session_state.knowledge_base.keys())
                random_term_key = random.choice(available_terms)
                selection_msg = f"Okay, let's talk about: '{random_term_key.title()}'"
                st.session_state.display_messages.append({"role": "assistant", "content": selection_msg})
                log_to_file(st.session_state.log_file, selection_msg, speaker="AI Agent")
                
                with st.spinner("AI is thinking..."):
                    ai_messages_list = process_ai_query(random_term_key.title(), random_term_key, 
                                                       st.session_state.chat_session, 
                                                       st.session_state.knowledge_base, 
                                                       st.session_state.log_file,
                                                       st.session_state.initial_chat_history_template) # Pass template
                for msg_info in ai_messages_list:
                    role = "assistant" 
                    if "speaker_type" in msg_info: 
                        s_type = msg_info["speaker_type"].lower()
                        if "local" in s_type: role = "assistant" 
                        elif "llm" in s_type: role = "assistant"
                        elif "system_info" in s_type: role = "assistant" 
                        elif "system_error" in s_type: role = "assistant" 
                    st.session_state.display_messages.append({"role": role, "content": msg_info["text"]})
            else:
                no_terms_msg = "My local knowledge base is empty."
                st.session_state.display_messages.append({"role": "assistant", "content": no_terms_msg})
                log_to_file(st.session_state.log_file, no_terms_msg, speaker="AI Agent")
            log_to_file(st.session_state.log_file, "---")
            
        else: # It's a query for the AI
            with st.spinner("AI is thinking..."):
                ai_messages_list = process_ai_query(user_query, user_query_lc, 
                                                   st.session_state.chat_session, 
                                                   st.session_state.knowledge_base, 
                                                   st.session_state.log_file,
                                                   st.session_state.initial_chat_history_template) # Pass template
            for msg_info in ai_messages_list:
                role = "assistant" 
                if "speaker_type" in msg_info: 
                    s_type = msg_info["speaker_type"].lower()
                    if "local" in s_type: role = "assistant" 
                    elif "llm" in s_type: role = "assistant"
                    elif "system_info" in s_type: role = "assistant" 
                    elif "system_error" in s_type: role = "assistant" 
                st.session_state.display_messages.append({"role": role, "content": msg_info["text"]})
        
        if should_rerun_after_processing:
            st.rerun()

if __name__ == '__main__':
    main()