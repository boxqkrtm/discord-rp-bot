import os
from dotenv import load_dotenv
import asyncio
from google import genai
from google.genai import types

load_dotenv()

class GeminiChat:
    def __init__(self, system=None, history=[]):
        self.client = genai.Client(
            api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
        )
        self.model = "gemini-2.0-flash"
        self.history = []
        self.last = None

        # Convert history format if provided
        if history:
            for msg in history:
                if msg["role"] == "user":
                    self.history.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg["parts"][0])]
                    ))
                elif msg["role"] == "model":
                    self.history.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg["parts"][0])]
                    ))

        # Setup configuration
        self.generate_content_config = types.GenerateContentConfig(
            temperature=0.9,
            top_p=1,
            top_k=1,
            max_output_tokens=4096,
            response_mime_type="text/plain",
        )

        # Add system instruction if provided
        if system:
            self.generate_content_config.system_instruction = [
                types.Part.from_text(text=system)
            ]

    def send_message(self, message):
        # Add user message to history
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)]
        )

        contents = self.history + [user_content] if self.history else [user_content]

        # Generate response
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self.generate_content_config,
        )

        # Add user message and response to history
        self.history.append(user_content)

        model_content = types.Content(
            role="model",
            parts=[types.Part.from_text(text=response.text)]
        )
        self.history.append(model_content)

        # Store last response for convenience
        self.last = SimpleResponse(response.text)

        return response.text

    async def send_message_async(self, message):
        """Asynchronous version of send_message"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.send_message, message)
        return result


class SimpleResponse:
    def __init__(self, text):
        self.text = text


def get_gemini_chat(system=None, history=[]):
    return GeminiChat(system=system, history=history)