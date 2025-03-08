import os
from dotenv import load_dotenv, set_key
import asyncio
from google import genai
from google.genai import types
from typing import List
from pathlib import Path

load_dotenv()

class GeminiChat:
    def __init__(self, system=None, history=[]):
        self.api_keys = self._load_api_keys()
        self.current_key_index = int(os.getenv("CURRENT_API_KEY_INDEX", "0"))
        self.env_path = Path('.env')
        self.setup_client()

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

    def _load_api_keys(self) -> List[str]:
        """API 키들을 로드합니다."""
        keys = []
        # 기본 API 키 추가
        main_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if main_key:
            keys.append(main_key)

        # 추가 API 키들 로드
        for i in range(2, 4):  # GOOGLE_API_KEY_2, GOOGLE_API_KEY_3
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if key:
                keys.append(key)

        if not keys:
            raise ValueError("No API keys found in environment variables")

        return keys

    def setup_client(self):
        """현재 선택된 API 키로 클라이언트를 설정합니다."""
        self.client = genai.Client(
            api_key=self.api_keys[self.current_key_index],
        )

    def switch_to_next_key(self) -> bool:
        """다음 API 키로 전환합니다. 성공 여부를 반환합니다."""
        next_index = (self.current_key_index + 1) % len(self.api_keys)
        if next_index != self.current_key_index:
            self.current_key_index = next_index
            # .env 파일에 현재 인덱스 저장
            set_key(self.env_path, "CURRENT_API_KEY_INDEX", str(self.current_key_index))
            self.setup_client()
            return True
        return False

    def send_message(self, message):
        max_retries = len(self.api_keys)
        retries = 0
        last_error = None

        while retries < max_retries:
            try:
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

                # return f"{self.current_key_index + 1}/{len(self.api_keys)}\n{response.text}"
                return f"{response.text}"

            except Exception as e:
                error_msg = f"API 키 오류 (현재 키: {self.current_key_index + 1}/{len(self.api_keys)}, 인덱스: {self.current_key_index}): {str(e)}"
                #print(error_msg)
                last_error = error_msg
                retries += 1

                self.switch_to_next_key()
                return f"{self.current_key_index + 1}/{len(self.api_keys)} {last_error}"

        raise Exception(f"모든 API 키가 실패했습니다. 마지막 오류: {last_error}")

    async def send_message_async(self, message):
        """Asynchronous version of send_message"""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.send_message, message)
        return result

class SimpleResponse:
    def __init__(self, text):
        self.text = text

def get_gemini_chat(system=None, history=[]):
    return GeminiChat(system=system, history=history)
