import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';

function Chat() {
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [limitReached, setLimitReached] = useState(false);

  const lastSpeechTimeRef = useRef(Date.now());
  const lastTranscriptRef = useRef("");
  const idlePromptGivenRef = useRef(false);

  useEffect(() => {
    const idleInterval = setInterval(() => {
      const now = Date.now();
      // If 15 seconds of silence and no idle prompt has been given, then speak an idle prompt
      if (now - lastSpeechTimeRef.current > 15000 && !idlePromptGivenRef.current) {
        console.log("DEBUG: Detected idle silence, giving idle prompt");
        speakText("I'm still here if you need me.");
        idlePromptGivenRef.current = true;
        // Optionally update lastSpeechTimeRef to avoid repeated prompts immediately
        lastSpeechTimeRef.current = now;
      }
    }, 5000); // check every 5 seconds
    return () => clearInterval(idleInterval);
  }, []);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Sorry, your browser doesn't support speech recognition.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.continuous = true; // Enable continuous listening

    recognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1];
      const transcript = lastResult[0].transcript.trim();
      const confidence = lastResult[0].confidence || 1; // fallback if undefined
    
      if (transcript.length < 3 || confidence < 0.6) {
        console.log("DEBUG: Ignoring low confidence or short result:", transcript, "Confidence:", confidence);
        return;
      }
      
      // Only send if the new transcript is different from the last one processed
      if (transcript === lastTranscriptRef.current) {
        console.log("DEBUG: Duplicate transcript detected, ignoring:", transcript);
        return;
      }
      lastTranscriptRef.current = transcript;
      
      console.log("DEBUG: Recognized:", transcript, "Confidence:", confidence);
      lastSpeechTimeRef.current = Date.now();
      idlePromptGivenRef.current = false;
      sendMessage(transcript);
    };

    recognition.onerror = (event) => {
      console.error("DEBUG: Speech recognition error:", event.error);
    };
    recognition.onend = () => {
      console.log("DEBUG: Speech recognition ended");
      if (listening) {
        // Automatically restart recognition for a continuous call experience
        console.log("DEBUG: Restarting speech recognition...");
        recognition.start();
      }
    };

    recognitionRef.current = recognition;
  }, [listening]);

  const sendMessage = async (text) => {
    console.log("DEBUG: Sending message:", text);
    try {
      const response = await axios.post("http://localhost:65432/api/chat", { message: text }, { withCredentials: true });
      console.log("DEBUG: Received response:", response.data);
      speakText(response.data.response);
    } catch (error) {
      console.error("DEBUG: Axios error response:", error.response);
      let errorMsg = "Error communicating with the server";
      if (error.response && error.response.data) {
        if (error.response.data.limitReached) {
          setLimitReached(true);
        }
        errorMsg = error.response.data.error || errorMsg;
      }
      console.log("DEBUG: Speaking error message:", errorMsg);
      speakText(errorMsg);
    }
  };

  const startContinuousRecognition = () => {
    if (recognitionRef.current && !listening) {
      recognitionRef.current.start();
      setListening(true);
      console.log("DEBUG: Continuous recognition started");
    }
  };

  const speakText = async (text) => {
    try {
      // Call our backend TTS endpoint
      const response = await axios.post(
        "http://localhost:65432/api/tts",
        { text },
        { responseType: "blob", withCredentials: true }
      );
      // Create a URL for the returned audio blob and play it
      const audioUrl = URL.createObjectURL(response.data);
      const audio = new Audio(audioUrl);
      audio.play();
      // Optionally, revoke the URL after playback
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
    } catch (error) {
      console.error("DEBUG: TTS error:", error);
    }
  };

  return (
    <div className="chat-container">
      {limitReached && (
        <div className="modal">
          <h2>Chat Limit Exceeded</h2>
          <p>You have been chatting for a while. Please sign up or log in to continue talking with Vivica.</p>
          {/* Insert sign-up/login links or a form here */}
        </div>
      )}
      <button className="mic-button" onClick={startContinuousRecognition} disabled={listening}>
        {listening ? "Listening..." : "Start Call"}
      </button>
    </div>
  );
}

export default Chat;