from flask import Flask, request, jsonify
from p2p import p2p_argument, call_number, summarize_with_ollama

app = Flask(__name__)

@app.route('/api/initiate-first-call', methods=['POST'])
def initiate_first_call():
    """Endpoint to initiate the first call to collect doctor's arguments"""
    data = request.json
    if not data or 'phone_number' not in data:
        return jsonify({"error": "Phone number is required"}), 400
    
    phone_number = data['phone_number']
    
    # Get doctor's arguments through the initial call
    argument = p2p_argument(phone_number)
    
    if not argument:
        return jsonify({"error": "Failed to get argument from initial call"}), 500
    
    return jsonify({
        "success": True,
        "argument": argument
    })

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """Endpoint to summarize the transcript"""
    data = request.json
    if not data or 'transcript' not in data:
        return jsonify({"error": "Transcript is required"}), 400
    
    transcript = data['transcript']
    summary = summarize_with_ollama(transcript)
    
    return jsonify({
        "success": True,
        "summary": summary
    })

@app.route('/api/make-p2p-call', methods=['POST'])
def make_p2p_call():
    """Endpoint to make the P2P call with the summarized prompt"""
    data = request.json
    if not data or 'phone_number' not in data or 'prompt' not in data:
        return jsonify({"error": "Phone number and prompt are required"}), 400
    
    phone_number = data['phone_number']
    prompt = data['prompt']
    
    transcript = call_number(phone_number, prompt)
    
    if not transcript:
        return jsonify({"error": "Failed to get transcript from P2P call"}), 500
    
    return jsonify({
        "success": True,
        "transcript": transcript
    })

@app.route('/api/complete-flow', methods=['POST'])
def complete_flow():
    """Endpoint that handles the entire flow: initial call, summarize, and P2P call"""
    data = request.json
    if not data or 'doctor_phone' not in data or 'p2p_phone' not in data:
        return jsonify({"error": "Doctor's phone number and P2P phone number are required"}), 400
    
    doctor_phone = data['doctor_phone']
    p2p_phone = data['p2p_phone']
    
    # Step 1: Call the doctor to get arguments
    argument = p2p_argument(doctor_phone)
    if not argument:
        return jsonify({"error": "Failed to get argument from initial call"}), 500
    
    # Step 2: Summarize the arguments
    summary = summarize_with_ollama(argument)
    if not summary:
        return jsonify({"error": "Failed to summarize argument"}), 500
    
    # Step 3: Make the P2P call
    p2p_transcript = call_number(p2p_phone, summary)
    if not p2p_transcript:
        return jsonify({"error": "Failed to get transcript from P2P call"}), 500
    
    return jsonify({
        "success": True,
        "initial_argument": argument,
        "summary": summary,
        "p2p_transcript": p2p_transcript
    })

if __name__ == "__main__":
    app.run(debug=True)
