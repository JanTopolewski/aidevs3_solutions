import asyncio
import os
import json

import requests
import aiofiles
from dotenv import load_dotenv
from openai import AsyncOpenAI

def get_sound_files_paths(directory):
    if os.path.exists(directory):
        files = []

        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            files.append(file_path)

        return files
    else:
        raise FileNotFoundError("Files folder not found")
        return None


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"mp3",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


async def read_text_file(file_path):
    async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
        text = await file.read()

    return text


async def transcribe_audio(file_path):
    print("Sending audio to Whisper")
    global file_number
    with open(file_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )

    async with aiofiles.open("transcriptions/przesluchanie_nr"+str(file_number)+".txt", "w", encoding="utf-8") as file:
        await file.write(transcription)
    file_number += 1


async def get_answer_from_gpt(user_prompt):
    system_prompt = '''You are an assistant whose task is to find out what street the institute where Professor Maj lectures is located. You must extract this information from the interviews given and from your own knowledge.
< rules>
- The answer will not be given to you literally. You will gain some knowledge and you have to determine from that what institute you are referring to. From your own knowledge, give the name of the street in one word as if you were finishing a phrase in Polish: "ulica ..."
- Answer with only one word. Therefore, you shouldn't use word "ulica"
</rules>'''

    ai_response = await client.chat.completions.create(
        model = "gpt-4o",
        messages = [
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": user_prompt}
        ]
    )
    return ai_response.choices[0].message.content


async def main():
    choice = input("Do you want to call Whisper for new transcriptions (Y/N): ").lower()

    if choice == "y" or choice == "yes":
        file_paths = get_sound_files_paths("przesluchania")

        await asyncio.gather(*(transcribe_audio(path) for path in file_paths))
    
    elif choice != "n" and choice != "no":
        print("Wrong input!")
        return

    if os.path.exists("transcriptions"):
        files = os.listdir("transcriptions")
        data = await asyncio.gather(*(read_text_file("transcriptions/"+file) for file in files))
        data = "\n- Interview: ".join(data)
        data = "- Interview: " + data

        print(f"Data for AI:\n{data}")

        response = await get_answer_from_gpt(data)
        print("Response from AI:", response)
        send_answer_to_server(response)
    else:
        print("Transcription is not available. Please start a connection to Whisper")
    
    



if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    file_number = 1
    asyncio.run(main())