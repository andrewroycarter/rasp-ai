import sys
import time
import io
from picamera2 import Picamera2, Preview
from openai import OpenAI
import base64

# Placeholder for importing necessary modules for button press, audio recording, and text-to-speech

conversation_history = []

client = OpenAI()


def take_photo():
    picam2 = Picamera2()
    picam2.start_and_capture_file("image.jpeg", show_preview=False)

    base64_photo_data = base64.b64encode(open("image.jpeg", "rb").read())

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
        messages=conversation_history, model="gpt-4-vision-preview"
    )

    return response


def send_photo_to_openai(photo_data):
    # Code to send the captured photo data back to OpenAI
    # You might need to encode the photo data and set up a proper structure to send it
    pass


def capture_audio():
    # Code to capture audio
    # Return the captured audio as text
    pass


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
    )
    return response


def process_response(response):
    # Process the response to check for a take_photo function call
    choice = response.choices[0]
    message = choice.message
    if message.function_call:
        if message.function_call.name == "take_photo":
            take_photo()
            return
    else:
        print(message.text)


def check_for_button_press():
    # Code to check if the button is pressed
    # Return True if pressed, False otherwise
    pass


def main():
    # while True:
    # if check_for_button_press():
    prompt_text = "What is it that I am looking at right now?"
    response = send_to_openai(prompt_text)
    process_response(response)


# time.sleep(0.1)  # Sleep to prevent high CPU usage


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

# def main():
#     response = client.chat.completions.create(
#         messages=[{"role": "user", "content": "What is it that I am looking at?"}],
#         model="gpt-3.5-turbo",
#         tools=[
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "take_photo",
#                     "description": "Gets a photo of what the user is looking at.",
#                     "parameters": {"type": "object", "properties": {}},
#                 },
#             }
#         ],
#     )
