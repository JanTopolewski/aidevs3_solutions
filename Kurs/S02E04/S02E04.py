import requests
import os
import asyncio
import shutil
import base64
import json

from openai import AsyncOpenAI
from dotenv import load_dotenv


def save_text(text, file_name):
    with open("processed_files/"+file_name, 'w') as file:
        file.write(text)
    print(f"saved file: {file_name}")


def get_file_paths(directory):
    if os.path.exists(directory):
        files = []

        for file in os.listdir(directory):
            if os.path.splitext(file)[1] in [".txt", ".png", ".mp3"]:
                file_path = os.path.join(directory, file)
                files.append({"path":file_path, "file_name":os.path.splitext(file)[0], "file_type":os.path.splitext(file)[1]})

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
        "task":"kategorie",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


def copy_file(file_path, file_name):
    shutil.copy(file_path, "processed_files/"+file_name+".txt")
    print(f"Copied file: {file_path}")


async def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def transcribe_audio(file_path, file_name):
    print("Sending audio to Whisper")
    with open(file_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return {"text": transcription, "file": file_name+".txt"}


async def interpret_image_via_ai(image_path, user_prompt, file_name):
    print("Sending image to AI")
    system_prompt = "You are the assistant reading the text from the photo as accurately as possible. Respond only with text from the photo."

    ai_response = await client.chat.completions.create(
        model = "gpt-4o-mini",
        temperature = 0.1,
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{await encode_image(image_path)}"
                        }
                    },
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ]
    )
    return {"text": ai_response.choices[0].message.content,"file": file_name+".txt"}


async def get_answer_from_gpt(user_prompt):
    print("Getting answer from AI")
    system_prompt = '''You are an assistant whose job is to assign categories to the text provided by the user.
<rules>.
- You can only answer with one word: people, hardware or none. You may not select any other category
- Select the people category if the user text is only about captured people
- Select the hardware category if the user text is only about repaired machine failures. Focus on choosing only the failure about hardware, not software
- Otherwise select the none category
</rules>'''

    ai_response = await client.chat.completions.create(
        model = "gpt-4o-mini",
        temperature = 0.1,
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ]
    )
    return ai_response.choices[0].message.content


async def main():
    choice = input("Do you want to process files before sorting? (Y/N or Yes/No): ")
    if choice.lower() == "y" or choice.lower() == "yes":
        for filename in os.listdir("processed_files"):
            file_path = os.path.join("processed_files", filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Error while removing file {file_path}. Reason: {e}')
                return


        files = get_file_paths("pliki_z_fabryki")
        tasks = []
        for file in files:
            if file["file_type"] == ".mp3":
                tasks.append(asyncio.create_task(transcribe_audio(file["path"], file["file_name"])))
            elif file["file_type"] == ".png":
                tasks.append(asyncio.create_task(interpret_image_via_ai(file["path"], "Give me the text from the picture.", file["file_name"])))
            elif file["file_type"] == ".txt":
                copy_file(file["path"], file["file_name"])

        results = await asyncio.gather(*tasks)

        for result in results:
            save_text(result["text"], result["file"])
        print("Saved all files")

    elif choice.lower() != "n" and choice.lower() != "no":
        print("Invalid choice!")
        return

    files = []
    file_types = []
    for file in os.listdir("pliki_z_fabryki"):
        files.append(os.path.splitext(file)[0])
        file_types.append(os.path.splitext(file)[1])
    
    people = []
    hardware = []
    for file in os.listdir("processed_files"):
        file_path = os.path.join("processed_files", file)

        with open(file_path, "r") as text_file:
            response = await get_answer_from_gpt(text_file.read())
        print(f"Repsonse for file {file}: {response}")

        if response == "people":
            index = files.index(os.path.splitext(file)[0])
            people.append(os.path.splitext(file)[0]+file_types[index])
        elif response == "hardware":
            index = files.index(os.path.splitext(file)[0])
            hardware.append(os.path.splitext(file)[0]+file_types[index])
        
    people.sort()
    hardware.sort()
    
    answer = {"people": people, "hardware": hardware}
    print("Answer:", answer)
    send_answer_to_server(answer)


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    asyncio.run(main())