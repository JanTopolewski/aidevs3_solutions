import json
import base64
import asyncio
import requests
import os

from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from dotenv import load_dotenv




async def transcribe_audio():
    print("Sending audio to Whisper")
    with open(file_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return {"text": transcription, "file": file_name+".txt"}


async def modify_audio(url):
    


async def download_and_modify_html_data(url):
    html_content = requests.get(url).text

    soup = BeautifulSoup(html_content, 'html.parser')

    tasks = []

    figure_list = soup.find_all('figure')
    audio_list = soup.find_all('audio')

    for figure in figure_list:
        tasks.append(asyncio.create_task())

    for figure in figure_list:
        tasks.append(asyncio.create_task())

    asyncio.gather(*tasks)


async def main():
    choice = input("Do you want to process data before answering? (Y/N or Yes/No): ")
    if choice.lower() == "y" or choice.lower() == "yes":
        

    elif choice.lower() == "n" and choice.lower() == "no":
        print("Invalid choice!")
        return


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())