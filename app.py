from flask import Flask, render_template, request, jsonify
import openai
import re
import tempfile
import os

transcription_buffer = []  # Buffer to hold continuous transcriptions

app = Flask(__name__)

try:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError:
    SOME_SECRET = "Token not available!"

# Initialize OpenAI client
openai.api_key = "OPENAI_API_KEY"

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
                    "content": "Return the most appropriate word based on the context and only return the word. "
                    + prompt,
                },
            ],
        )
        completion = response.choices[0].message.content.strip()
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
    transcribed_text = transcribe_audio(audio_chunk_path)

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

        suggestion = ""
        if stutter_detected:
            suggestion = (
                handle_stutter_detection()
            )  # Assuming this function now directly uses `transcribed_text`

        os.remove(temp_path)  # Clean up the temporary file after processing

        # Respond with the transcription and any detected stutter patterns
        return jsonify({"transcription": transcribed_text, "suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
