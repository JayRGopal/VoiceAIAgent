import requests
import time

# Use the API key directly in the code
API_KEY = "org_72a2a3d7228bc7c57ad064f403344d41231de43d9517485a2ad52d8da66035d07167bf2e60654ddcc8b369"

CALL_P2P_PROMPT = """
You are a doctor calling another doctor in a peer-to-peer prior authorization denial call. 
Your task is to present a solid argument for why the requested procedure/medication should be authorized. 
Do not reveal that you are an AI at any point in the conversation. 
Provide a clear explanation of why authorization is essential, citing specific reasons from the argument provided.
Here is a conversation of user (doctor) and assistant outlining what the doctor wishes to get an authorization and the reasons behind it: {argument}
Take this transcript, distill it into an argument and convince the doctor that the requested procedure/medication should be authorized.
Ensure the argument is professional, evidence-based, and persuasive. 
"""

CALL_FOR_ARGUMENT = """
You are an AI assistant calling a doctor who wishes to get prior authorization for an imaging study.
Ask the doctor their name and their patient's name. Ask what they wish to get prior authorization for, and the reasoning behind it. Why is it medically necessary?
After the doctor gives their reasons, play devil's advocate and ask 1-2 questions that questions the doctor's logic.
Once you've extracted the reason for authorization and reasoning, end the conversation with the doctor. End it promptly! The doctor has very little time."""


def p2p_argument(phone_number=None):
    """
    Initial call to the doctor that wants authorization to extract information about the necessary authorization.
    Now accepts phone_number as a parameter for API usage.
    """
    if not phone_number:
        phone_number = input("Please input your phone number: ")
    
    print(f"Initiating call to {phone_number} for doctor's argument")
    initial_transcript = call_number(phone_number, CALL_FOR_ARGUMENT)
    return initial_transcript


def call_number(phone_number, prompt):
    """Make a call to the provided phone number with the given prompt"""
    url = "https://api.bland.ai/v1/calls"

    payload = {
        "phone_number": phone_number,
        "task": prompt,
        "voice": "Josh",
        "wait_for_greeting": False,
        "block_interruptions": False,
        "interruption_threshold": 100,
        "model": "enhanced",
        "temperature": 0.3,
        "dynamic_data": [],
        "language": "en-US",
        "max_duration": 2,
    }

    headers = {
        "authorization": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        print(f"Making API call to Bland.ai for phone number: {phone_number}")
        response = requests.post(url, json=payload, headers=headers)
        print(f"Bland.ai API response status: {response.status_code}")

        if response.status_code == 200:
            call_data = response.json()
            call_id = call_data.get("call_id")
            if call_id:
                print(f"Call initiated successfully! Call ID: {call_id}")
                # Wait for the call to complete before fetching the transcript
                return wait_for_transcript(call_id)
            else:
                print("Error: No call_id returned.")
                return None
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None


def wait_for_transcript(call_id, check_interval=5, timeout=600):
    """Polls the API until the call is completed and retrieves the transcript."""
    url = f"https://api.bland.ai/v1/calls/{call_id}"
    headers = {
        "authorization": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"Waiting for call {call_id} to complete...")
    elapsed_time = 0
    while elapsed_time < timeout:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                call_details = response.json()
                status = call_details.get("status", "")
                print(f"Call status: {status}")

                if status == "completed":
                    transcript = call_details.get("concatenated_transcript", "No transcript available")
                    print("\nCall Transcript:\n", transcript)
                    return transcript
                elif status == "failed":
                    print("Call failed. No transcript available.")
                    return None
            else:
                print(f"Error retrieving call status: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")

        time.sleep(check_interval)
        elapsed_time += check_interval
        print(f"Waited {elapsed_time} seconds...")

    print("Timed out waiting for the call to complete.")
    return None


def summarize_with_ollama(transcript):
    """Use Ollama to summarize the transcript"""
    url = "http://localhost:11434/api/generate"

    formatted_prompt = CALL_P2P_PROMPT.format(argument=transcript)
    
    payload = {
        "model": "llama3",  # or "mistral", "gemma" etc.
        "prompt": formatted_prompt,
        "stream": False
    }
    
    try:
        print("Sending transcript to Ollama for summarization...")
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            summary = result.get('response', 'No summary generated.')
            print("Summarization complete.")
            return summary
        else:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return "Error generating summary."
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        return "Connection error."


# This allows the script to be run directly for testing
if __name__ == "__main__":
    def main():
        # Receive doctor's arguments
        phone_number = input("Please input your phone number: ")
        argument = p2p_argument(phone_number)
        print(argument)

        new_prompt = summarize_with_ollama(argument)
        p2p_number = input("Please input the phone number of who you wish for me to call: ")

        # Call number and return transcript
        call_number(p2p_number, new_prompt)

    main()
