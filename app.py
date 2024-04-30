from flask import Flask, render_template, request, jsonify, send_file
import openai
import re
import tempfile
import os
from pathlib import Path

transcription_buffer = []  # Buffer to hold continuous transcriptions

app = Flask(__name__)

try:
    OPENAI_API_KEY = os.getenv('API_KEY')
except Exception as e:
    SOME_SECRET = "Token not available!"

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

"""
Transcription through whisper
"""



def transcribe_audio(file_path):
    try:
        response = openai.audio.transcriptions.create(
            file=open(file_path, "rb"),
            model="whisper-1",
            prompt="So uhm, yeaah. ehm, uuuh. like.",
        )
        return response.text
    except Exception as e:
        return str(e)


"""
GPT word retrieval 
"""


def get_completion(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": "You are a assisant trying to help patients with aphasia communicate. You will be provided a transcript of a users communication.Return the words that finish the sentence or the word the user is trying to describe based on the context. But only return the top 10 words and nothing else. "
                    + prompt,
                },
            ],
        )
        completion = response.choices[0].message.content.strip()
        print(response)
        return completion
    except Exception as e:
        return str(e)


"""
Stutter detection
"""


def detect_stutter_patterns():
    text = " ".join(transcription_buffer)
    text = re.sub(r"(\b\w\b)\.\s*", r"\1 ", text)
    text = re.sub(r"(\w)-\s*", r"\1 ", text)

    repetition_pattern = r"(\b\w+\b)(?:\s+\1\b)+"  # Words repeated consecutively
    prolongation_pattern = r"(\w)\1{2,}"  # Characters repeated more than twice
    interjection_pattern = r"\b(uh|um|ah|uhh|ahh|umm)\b"  # Common interjections# New patterns for stutter detection

    # Detect
    repetitions = re.findall(repetition_pattern, text)
    prolongations = re.findall(prolongation_pattern, text)
    interjections = re.findall(interjection_pattern, text)

    # Return detected patterns
    detected = {
        "repetitions": repetitions,
        "prolongations": prolongations,
        "interjections": interjections,
    }
    return any(detected.values())


"""
Word retrieval after stutter detection
"""


def handle_stutter_detection():
    combined_text = " ".join(transcription_buffer)
    response = get_completion(combined_text)
    # Clear the buffer after processing
    transcription_buffer.clear()
    return response


"""
Processing chunks of audio
"""


def process_transcription_chunk(audio_chunk_path):
    global transcription_buffer
    # transcribed_text = transcribe_audio(audio_chunk_path)

    #For Testing
    transcribed_text = "I am, I am really hungry. I want to eat, uh, uh, uh, uh."

    # Append transcription to a buffer for potentially accumulating more context
    transcription_buffer.append(transcribed_text)

    return transcribed_text


"""
Front End Code below
"""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/record", methods=["POST"])
def record():
    if "audio-file" not in request.files:
        print("No audio file provided")
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio-file"]

    # Save the incoming audio chunk to a temporary file
    _, temp_path = tempfile.mkstemp(suffix=".wav")
    audio_file.save(temp_path)

    try:
        # Transcribe the audio chunk
        transcribed_text = process_transcription_chunk(temp_path)
        stutter_detected = detect_stutter_patterns()

        print(transcribed_text)
        print(stutter_detected)

        stutter_detected = True

        suggestion = ""
        if stutter_detected:
            suggestion = get_completion(" ".join(transcription_buffer))
            suggestion = (

                handle_stutter_detection()
                # get_completion(transcribed_text)
            )  # Assuming this function now directly uses `transcribed_text`

        os.remove(temp_path)  # Clean up the temporary file after processing

        # Respond with the transcription and any detected stutter patterns
        return jsonify({"transcription": transcribed_text, "suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/synthesize', methods=['POST'])
def synthesize_audio():
    text = request.json['text']
    print(text)
    try:
        speech_file_path = Path(__file__).parent / f"{text}.mp3"
        response = openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        response.stream_to_file(speech_file_path)
        return send_file(speech_file_path, as_attachment=True, download_name=f"{text}.mp3")
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=True)
