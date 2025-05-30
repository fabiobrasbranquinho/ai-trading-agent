# File: my_ai_agent_logic.py
import json
import datetime
import random
# Note: google.generativeai is not strictly needed here if 'current_chat_obj' is always passed in
# and this file doesn't initialize models itself. But it's fine for type hinting or future use.
import google.generativeai as genai

# --- Function to Load Data From File ---
def load_data_from_file(filename, file_type="txt"):
    """
    Loads data from a specified file.
    Can handle plain text (.txt) or JSON (.json) files.
    Returns sensible defaults (empty string for txt, empty list for json) if loading fails.
    """
    print(f"Attempting to load {file_type.upper()} data from '{filename}'...") # Console log for debugging
    try:
        with open(filename, "r", encoding="utf-8") as f:
            if file_type.lower() == "json":
                data = json.load(f)
            elif file_type.lower() == "txt":
                data = f.read()
            else:
                print(f"Warning: Unsupported file_type '{file_type}' for '{filename}'. Reading as plain text.")
                data = f.read()
        print(f"Successfully loaded data from '{filename}'.") # Console log
        return data
    except FileNotFoundError:
        print(f"ERROR: File '{filename}' not found. Returning default for {file_type.upper()}.")
        if file_type.lower() == "json": return []
        else: return ""
    except json.JSONDecodeError as e:
        print(f"ERROR decoding JSON from '{filename}': {e}. Returning default empty list.")
        return []
    except Exception as e:
        print(f"ERROR loading data from '{filename}' (type: {file_type}): {e}.")
        if file_type.lower() == "json": return []
        else: return ""

# --- Function: Log to File ---
def log_to_file(log_filename, message, speaker=None):
    """Logs a message to the specified file.
       If a speaker is provided, it prefixes the message.
    """
    try:
        with open(log_filename, "a", encoding="utf-8") as f:
            if speaker:
                f.write(f"{speaker}: {message}\n")
            else:
                f.write(f"{message}\n")
    except Exception as e_log:
        print(f"Error writing to log file '{log_filename}': {e_log}") # Console log for error

# --- Function: Get Help Text Content (for UI) ---
def get_help_for_ui(loaded_help_text_from_file, log_filename):
    """Logs that help was requested and returns the help message string."""
    log_to_file(log_filename, "--- User typed /help ---")
    log_to_file(log_filename, "Displayed help message.", speaker="System")
    log_to_file(log_filename, "-" * 30)
    return loaded_help_text_from_file

# --- Function: Get My Terms List Text (for UI) ---
def get_my_terms_list_text(knowledge_base, log_filename):
    """Returns a string listing predefined terms or a 'not found' message, and logs."""
    log_to_file(log_filename, "--- User typed /my_terms ---")
    if knowledge_base:
        terms_list_message = "I have predefined definitions for these terms:\n" + "\n".join(
            [f"- {term.title()}" for term in knowledge_base.keys()]
        )
        log_to_file(log_filename, terms_list_message, speaker="AI Agent")
        log_to_file(log_filename, "-" * 30)
        return terms_list_message
    else:
        no_terms_message = "My local knowledge base of terms is currently empty."
        log_to_file(log_filename, no_terms_message, speaker="AI Agent")
        log_to_file(log_filename, "-" * 30)
        return no_terms_message

# --- Function: Process AI Query (for UI) ---
def process_ai_query(user_query_original, user_query_lower, current_chat_obj,
                    knowledge_base, log_filename, persona_initial_history):
    """
    Checks local KB, prepares prompt, queries AI.
    Returns a list of message dictionaries for the UI.
    Each dict: {"speaker_type": "user/local/llm/system_info/system_error", "text": "message_content"}
    """
    messages_for_ui = []
    prompt_for_ai = user_query_original # Default prompt for AI

    # Attempt to extract the specific term for KB lookup
    term_to_explain_lower = user_query_lower
    if user_query_lower.startswith("what is ") or user_query_lower.startswith("explain "):
        parts = user_query_original.split(" ", 2)
        if len(parts) > 1:
            term_to_explain_lower = " ".join(parts[1:]).lower()

    if term_to_explain_lower in knowledge_base:
        predefined_definition = knowledge_base[term_to_explain_lower]
        display_term = term_to_explain_lower.title()
        local_def_message = f"From my local knowledge: {display_term} is defined as - \"{predefined_definition}\"."
        messages_for_ui.append({"speaker_type": "local", "text": local_def_message})
        log_to_file(log_filename, local_def_message, speaker="AI Agent (Local)")
        
        # Use the persona's instruction style for elaboration
        elaboration_instruction = persona_initial_history[0]['parts'][0]['text'] # Get the user instruction part of persona
        # This is a bit of a simplification; ideally, you'd have a clearer way to define this specific follow-up prompt.
        # For now, we'll use a generic elaboration prompt based on the persona's goal.
        prompt_for_ai = (f"The user asked about '{display_term}'. "
                         f"My local knowledge says: '{predefined_definition}'. {elaboration_instruction}")
    #else:
        #not_found_msg = f"I don't have a predefined definition for '{user_query_original}'. I'll ask the AI for an explanation based on its general knowledge and persona..."
        #messages_for_ui.append({"speaker_type": "system_info", "text": not_found_msg})
        #log_to_file(log_filename, not_found_msg, speaker="AI Agent")
        # prompt_for_ai remains user_query_original, AI will use its persona set in initial_chat_history

    try:
        # print(f"\n>>> Sending to AI: '{prompt_for_ai}'") # For debugging
        response = current_chat_obj.send_message(prompt_for_ai)
        ai_response_text = ""
        try:
            ai_response_text = response.text
        except ValueError: # Handles blocked content
            ai_response_text = "[LLM Response blocked or contained no valid text content]"
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                ai_response_text += f"\nPrompt Feedback: {response.prompt_feedback}"
        except Exception as e_text:
            ai_response_text = f"[Error accessing LLM response text: {e_text}]"
        
        messages_for_ui.append({"speaker_type": "llm", "text": ai_response_text})
        log_to_file(log_filename, ai_response_text, speaker="AI Agent (LLM)")
        log_to_file(log_filename, "-" * 30)
    except Exception as e_send:
        error_msg = f"An error occurred sending message or generating content: {e_send}"
        messages_for_ui.append({"speaker_type": "system_error", "text": error_msg})
        log_to_file(log_filename, error_msg, speaker="System Error")
        log_to_file(log_filename, "-" * 30)
        messages_for_ui.append({"speaker_type": "system_info", "text": "Please check your input or try again."})
    
    return messages_for_ui


if __name__ == "__main__":
    # This block is for testing my_ai_agent_logic.py directly if you want.
    # It won't run when imported by agent_ui.py.
    # To use this as a module for Streamlit, ensure no interactive loop runs here by default.
    print("my_ai_agent_logic.py functions are defined. This file is intended to be imported as a module.")
    # You can add test calls to your functions here if you like, for example:
    # test_log_file = "test_logic_log.txt"
    # print(get_help_text_for_ui("This is test help text.", test_log_file))
    # test_kb = {"test term": "a term for testing"}
    # print(get_my_terms_list_text(test_kb, test_log_file))
    pass