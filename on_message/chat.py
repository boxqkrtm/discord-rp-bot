# import
import pickle
import traceback
import datetime
import re
import os
import discord
from dotenv import load_dotenv
load_dotenv()

# util
from llm.gemini_llm import get_gemini_chat
from util.message_util import send_message_in_chunks

# Get available emojis from img folder
def get_available_emojis():
    emoji_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')
    available_emojis = []
    if os.path.exists(emoji_path):
        for file in os.listdir(emoji_path):
            if file.endswith('.png'):
                emoji_name = os.path.splitext(file)[0]
                available_emojis.append(emoji_name)
    return available_emojis

# Extract emoji tags from response
def extract_emoji_tags(response):
    pattern = r'\[이모지:(.*?)\]'
    matches = re.findall(pattern, response)
    if len(matches) == 0:
        pattern = r'\[이모ji:(.*?)\]'
        matches = re.findall(pattern, response)
    return matches

# Send emoji image
async def send_emoji(message, emoji_name):
    emoji_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', f'{emoji_name}.png')
    if os.path.exists(emoji_path):
        await message.channel.send(file=discord.File(emoji_path))
        return True
    return False

# init variable
def save_llm_history():
    global llmHistory
    with open('llm_history.pkl', 'wb') as f:
        pickle.dump(llmHistory, f)

def load_llm_history():
    global llmHistory
    try:
        with open('llm_history.pkl', 'rb') as f:
            llmHistory = pickle.load(f)  # 저장된 메시지 배열을 그대로 로드
    except:
        llmHistory = {}

llmHistory = {} if 'llmHistory' not in globals() else llmHistory
try:
    load_llm_history()
except:
    print("Failed to load llm history")

llmUserCooltime = {}
llmIsRunning = {}
llmDelay = 1

async def main(message, client):
    global ssh_credentials
    guildId = message.guild.id
    userLastMessage = message.content
    try:
        nowtime = datetime.datetime.now()
        # init dict
        if guildId in llmUserCooltime:
            pass
        else:
            llmUserCooltime[guildId] = nowtime - datetime.timedelta(
                seconds=llmDelay
            )
        return await eong_chat_funcion(message, guildId, userLastMessage, client)
    except Exception as e:
        print(e)
        # print stack trace
        print(traceback.format_exc())

def reset_llm(guildId):
    global ssh_credentials, llmHistory
    # 해당 guildId의 대화 기록 초기화
    llmHistory[guildId] = []  # 새로운 빈 메시지 배열로 시작

    # 변경된 llmHistory 저장
    try:
        save_llm_history()
    except Exception as e:
        print(f"Failed to save llm history after reset: {e}")

async def aync_gemini_chat(userLastMessage, gchat):
    await gchat.send_message_async(userLastMessage)
    response = gchat.last.text
    return response

async def eong_chat_funcion(message, guildId, userLastMessage, client):
    # 트리거 단어
    # Define trigger word
    trigger_word = "<<"

    # Check if message starts with the trigger word
    if userLastMessage.startswith(trigger_word):
        if len(userLastMessage) > len(trigger_word):
            userLastMessage = userLastMessage[len(trigger_word):]
    else:
        return

    if guildId in llmIsRunning:
        response = "님꺼 생각중임 ㄱㄷ"
    elif userLastMessage.startswith("초기화"):
        if message.author.guild_permissions.administrator or message.author.name == "poca_p0ca":
            llmHistory[guildId] = []  # 메시지 배열 초기화
            save_llm_history()
            await message.channel.send(content="[SYSTEM] 초기화 했다요")
        else:
            await message.channel.send(content="[SYSTEM] 권한이 없다요")
    elif userLastMessage.strip() != "":
        userLastMessage = f"<sender_id>{str(message.author.id)}\n<sender_name>{str(message.author.display_name)}\n{userLastMessage}"
        async with message.channel.typing():
            llmIsRunning[guildId] = 1
            nowtime = datetime.datetime.now()
            llmUserCooltime[guildId] = nowtime - datetime.timedelta(
                        seconds=60
                    )
            if not (guildId in llmHistory):
                llmHistory[guildId] = []  # 새 대화 시작시 빈 배열로 초기화

            # 대화 기록으로 chat 객체 생성
            chat = None
            adminid=None

            # Get available emojis
            available_emojis = get_available_emojis()

            # 프롬프트 파일 경로
            prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompt')

            # emoji_instructions 읽기
            emoji_instructions = ""
            if available_emojis:
                with open(os.path.join(prompt_dir, 'emoji_instructions.txt'), 'r', encoding='utf-8') as f:
                    emoji_instructions = f.read().replace('{available_emojis}', ", ".join(available_emojis))

            # adina 프롬프트 읽기
            with open(os.path.join(prompt_dir, 'adina.txt'), 'r', encoding='utf-8') as f:
                adina = f.read() + "\n" + emoji_instructions

            chat = get_gemini_chat(history=llmHistory[guildId], system=adina)

            try:
                # 사용자 메시지 저장
                if userLastMessage != "":
                    llmHistory[guildId].append({
                        "role": "user",
                        "parts": [userLastMessage]
                    })

                # 메시지 전송 및 응답 받기
                response = await chat.send_message_async(userLastMessage)
                aio = response

                # AI 응답 저장
                if aio.strip() != "":
                    llmHistory[guildId].append({
                        "role": "model",
                        "parts": [aio]
                    })

                # 이모지 태그 처리
                emoji_tags = extract_emoji_tags(aio)
                clean_response = aio
                for tag in emoji_tags:
                    clean_response = clean_response.replace(f'[이모지:{tag}]', '')
                    await send_emoji(message, tag)
                    break

                # 정제된 응답 전송
                clean_response = clean_response.strip()
                if clean_response:
                    await send_message_in_chunks(message, clean_response)

                nowtime = datetime.datetime.now()
            except Exception as e:
                await message.channel.send("error")
                print(e)
                print(traceback.format_exc())

                llmUserCooltime[guildId] = nowtime - datetime.timedelta(
                            seconds=llmDelay
                        )
        llmUserCooltime[guildId] = nowtime
        try:
            save_llm_history()  # 대화가 끝날 때마다 저장
        except Exception as e:
            print(f"Failed to save llm history: {e}")
        llmIsRunning.pop(guildId, None)
