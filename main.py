import sys
import os
import subprocess
from gpiozero import Button
import speech_recognition as sr

try:
    from picamera2 import Picamera2
except ImportError:
    print("Failed to import picamera2. Please install it with `pip3 install picamera2`.")

from openai import OpenAI
import base64

client = OpenAI()

class HardwareInterface:
    def take_photo(self):
        pass

    def capture_user_input(self):
        pass


class SimulatedHardware(HardwareInterface):
    def take_photo(self):
        path = input("Enter a file path for a photo: ")
        if not os.path.exists(path):
            print("Invalid file path.")
            return self.take_photo()
        base64_photo_data = base64.b64encode(open(path, "rb").read()).decode("utf-8")
        return base64_photo_data

    def capture_user_input(self):
        text = input("Enter a prompt: ")
        return text


class RaspberryPiZeroW(HardwareInterface):
    def __init__(self):
        self.button = Button(27)  # GPIO pin 27
        self.recording_process = None
        self.button.when_pressed = self.toggle_recording
        self.audio_file_path = 'recording.wav'

    def take_photo(self):
        picam2 = Picamera2()
        config = picam2.create_preview_configuration()
        config["main"]["size"] = (1280, 720)
        picam2.configure(config)
        picam2.start_and_capture_file("image.jpeg", show_preview=False)
        base64_photo_data = base64.b64encode(open("image.jpeg", "rb").read()).decode("utf-8")
        return base64_photo_data

    def capture_user_input(self):
        while self.recording_process is not None:
            pass
        return self.audio_to_text(self.audio_file_path)

    def toggle_recording(self):
        if self.recording_process is None:
            if os.path.exists(self.audio_file_path):
                os.remove(self.audio_file_path)
            self.recording_process = subprocess.Popen(['arecord', '-D', 'plughw:1,0', '-f', 'cd', '-t', 'wav', self.audio_file_path])
            print("Recording started...")
            time.sleep(0.5)  # Allow time for the recording process to start
        else:
            self.recording_process.terminate()
            self.recording_process = None
            print("Recording stopped.")
            time.sleep(0.5)  # Allow time for the file to be saved

    def audio_to_text(self, audio_file_path):
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file_path) as source:
            audio = recognizer.record(source)
            try:
                return recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                return "Speech Recognition could not understand audio"
            except sr.RequestError as e:
                return f"Could not request results from Speech Recognition service; {e}"


conversation_history = [
    {
        "role": "system",
        "content": "You are a personal assistant bot. The user is wearing a device that is connected to a camera, speakers, and a microphone. The user may ask you general questions, or questions about what they see. You will be provided with functions that will allow you to gather more information about the user.",
    },
]

def send_to_openai(prompt_text):
    global conversation_history
    conversation_history.append({"role": "user", "content": prompt_text})
    response = client.chat.completions.create(
        messages=conversation_history,
        model="gpt-4-1106-preview",
        functions=[
            {
                "name": "take_photo",
                "description": "Captures and returns a photo of what the user is looking at.",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
        max_tokens=4000,
    )
    return response


def send_photo_to_openai(base64_photo_data):
    global conversation_history
    image_history = conversation_history + [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_photo_data}",
                        "detail": "high",
                    },
                }
            ]
        }
    ]

    response = client.chat.completions.create(
        messages=image_history,
        model="gpt-4-vision-preview",
        max_tokens=4000,
    )

    return response


def process_response(response, device):
    choice = response.choices[0]
    message = choice.message
    if message.function_call:
        if message.function_call.name == "take_photo":
            photo_data = device.take_photo()
            photo_response = send_photo_to_openai(photo_data)
            process_response(photo_response, device)
            return
    else:
        text_to_speech(message.content)
        print(message.content)

def text_to_speech(text):
    wav_path = "/tmp/temp_speech.wav"
    amplified_wav_path = "/tmp/temp_speech_amplified.wav"
    os.system(f'espeak -w {wav_path} "{text}"')
    os.system(f'sox {wav_path} {amplified_wav_path} vol 1.2')
    os.system("amixer sset 'Master' 100%")
    os.system(f'aplay {amplified_wav_path}')


def main():
    device = RaspberryPiZeroW()
    print("Ready")
    while True:
        prompt_text = device.capture_user_input()
        response = send_to_openai(prompt_text)
        process_response(response, device)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
