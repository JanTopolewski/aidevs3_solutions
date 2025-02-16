import asyncio
import requests
import os
import json

from openai import AsyncOpenAI
from dotenv import load_dotenv


def save_image(url):
    print("Saving image")
    image_data = requests.get(url).content
    with open("generated_image.png", "wb") as file:
        file.write(image_data)

    print("Image saved as generated_image.png")


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"robotid",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


def get_data(url):
    response = requests.get(url)

    if response.status_code == 200:
        with open("data.json", "w", encoding="utf-8") as file:
            json.dump(response.json(), file, indent=4, ensure_ascii=False)
        print("JSON is saved to a file: data.json")
    else:
        response.raise_for_status()


async def generate_image(data):
    response = await client.images.generate(
        model="dall-e-3",
        prompt=f"Generate a robot image from the given description: {data["description"]}",
        size="1024x1024",
        quality="standard",
        n=1
    )
    print(f"Generated an image: {response.data[0].url}")
    return response.data[0].url


async def main():
    get_data("secret_endpoint")
    with open("data.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    response_url = await generate_image(data)
    print("Sending answer to server")
    send_answer_to_server(response_url)
    save_image(response_url)
    

if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())