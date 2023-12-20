import sys
import time
import io
import os

try:
    from picamera2 import Picamera2, Preview
except ImportError:
    print(
        "Failed to import picamera2. Please install it with `pip3 install picamera2`."
    )

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
        # Ask the user for input to a file path for a photo
        path = input("Enter a file path for a photo: ")
        # Ensure that the file path is valid, and a file exists at that path
        if not os.path.exists(path):
            print("Invalid file path.")
            return self.take_photo()

        base64_photo_data = base64.b64encode(open(path, "rb").read()).decode("utf-8")
        return base64_photo_data

    def capture_user_input(self):
        text = input("Enter a prompt: ")
        return text


class RaspberryPiZeroW(HardwareInterface):
    def take_photo(self):
        picam2 = Picamera2()
        
        # Define the configuration for a lower resolution
        config = picam2.create_preview_configuration()
        config["main"]["size"] = (1280, 720)  # Set to 1280x720 resolution

        # Configure the camera with the specified settings
        picam2.configure(config)

        picam2.start_and_capture_file("image.jpeg", show_preview=False)
        base64_photo_data = base64.b64encode(open("image.jpeg", "rb").read()).decode("utf-8")
        return base64_photo_data

    def capture_user_input(self):
        text = input("Enter a prompt: ")
        return text

conversation_history = [
    {
        "role": "system",
        "content": "You are a personal assistant bot. The user is wearing a device that is connected to a camera, speakers, and a microphone. The user may ask you general questions, or questions about what they see. You will be provided with functions that will allow you to gather more information about the user.",
    },
]

def send_to_openai(prompt_text):
    global conversation_history
    conversation_history.append({"role": "user", "content": prompt_text})

    # Also defines a function called capture_photo to send to GPT
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

    conversation_history.append(
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
            ],
        }
    )

    response = client.chat.completions.create(
        messages=conversation_history,
        model="gpt-4-vision-preview",
        max_tokens=4000,
    )

    return response


def process_response(response, device):
    # Process the response to check for a take_photo function call
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

    # Generate WAV file with espeak
    os.system(f'espeak -w {wav_path} "{text}"')

    # Amplify the volume of the WAV file
    os.system(f'sox {wav_path} {amplified_wav_path} vol 2.0')

    # Set volume to maximum
    os.system("amixer sset 'Master' 100%")

    # Play the amplified WAV file
    os.system(f'aplay {amplified_wav_path}')

def check_for_button_press():
    # Code to check if the button is pressed
    # Return True if pressed, False otherwise
    pass


def main():
    device = RaspberryPiZeroW()

    while True:
        prompt_text = device.capture_user_input()
        response = send_to_openai(prompt_text)
        process_response(response, device)


# time.sleep(0.1)  # Sleep to prevent high CPU usage


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
