import requests
import time


### Things to tweak:
## 1. use LLM to summarize information in transcript to provide to Bland for P2P Call
## 2. take in phone number of P2P during initial call, not as an input
## 3. prompt engineering + put API_KEY into environment variable


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


def p2p_argument():
    # initial call to the doctor that wants to authorization to extract information about the necesary authorization
    number = input("Please input your phone number: ")
    initial_transcript = call_number(number, CALL_FOR_ARGUMENT)

    return initial_transcript


def call_number(phone_number, prompt):
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
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            call_data = response.json()
            call_id = call_data.get("call_id")
            if call_id:
                print(f"Call initiated successfully! Call ID: {call_id}")
                # Wait for the call to complete before fetching the transcript
                return wait_for_transcript(call_id)
            else:
                print("Error: No call_id returned.")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

def wait_for_transcript(call_id, check_interval=5, timeout=600):
    """Polls the API until the call is completed and retrieves the transcript."""
    url = f"https://api.bland.ai/v1/calls/{call_id}"
    headers = {
        "authorization": API_KEY,
        "Content-Type": "application/json"
    }

    elapsed_time = 0
    while elapsed_time < timeout:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                call_details = response.json()
                status = call_details.get("status", "")

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

    print("Timed out waiting for the call to complete.")
    return None

def summarize_with_ollama(transcript):
    url = "http://localhost:11434/api/generate"

    formatted_prompt = CALL_P2P_PROMPT.format(argument=transcript)
    refine_prompt = f"Given the following prompt:\n\n'''{formatted_prompt}'''\n\nExplain the pros and cons of this prompt, and then give back a better prompt that's long and thorough yet concise."
    
    
    payload = {
        "model": "llama3",  # or "mistral", "gemma" etc.
        "prompt": refine_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'No summary generated.')
        else:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return "Error generating summary."
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        return "Connection error."
