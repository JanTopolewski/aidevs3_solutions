import os
import asyncio
import base64

from dotenv import load_dotenv
from openai import AsyncOpenAI


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def process_images(image_paths):
    images = []
    for image_path in image_paths:
        images.append({"type":"image_url", "image_url":{"url": f"data:image/jpeg;base64,{encode_image(image_path)}"}})
    print("Processed images")
    return images


async def get_answer_from_gpt(images, user_prompt):
    system_prompt = '''You are the assistant whose job it is to determine which city is referred to in the images.

<objective>.
Write out as briefly as possible (preferably in one word) the name of the city that is shown in the pictures given to you. 
</objective>

<rules>.
- One of the pictures may be wrong and refer to a different city. Consider the city that occurs more times
- Focus only on analysing the pictures, taking into account the hints from the user and using your own knowledge to determine which city is being referred to
</rules>
'''

    ai_response = await client.chat.completions.create(
        model = "gpt-4o",
        temperature = 0.1,
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": [
                    *images,
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ]
    )
    return ai_response.choices[0].message.content


async def main():
    if os.path.exists("images"):
        file_paths = []
        for file in os.listdir("images"):
            file_path = os.path.join("images", file)
            file_paths.append(file_path)

        images = process_images(file_paths)
        
        response = await get_answer_from_gpt(images, "Give me the name of the city shown on the maps. There are storehouses and fortresses in a given city.")
        print("Response from AI:", response)
    else:
        print("No directory like 'images' found")


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())
