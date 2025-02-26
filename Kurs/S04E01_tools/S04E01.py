import asyncio
import json
import requests
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI


def send_answer_to_server_or_get_image(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"photos",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())
    return server_response.json()


async def get_right_image(image_data):
    max_ai_requests_number = 6
    ai_requests_number = 0
    system_prompt = """You are an assistant whose job it is to decide how and if it is necessary to improve or repair the given photo.

<rules>.
- You can only answer using one word
- Each word will trigger a different tool to repair the photo
- You have a choice of:
    - 'REPAIR', which will repair noise and glitches. Use it when the presence of such anomalies makes it impossible to describe the person in the photo
    - 'DARKEN', which will darken the photo. Use it when the photo will be too bright to describe the person in the photo
    - 'BRIGHTEN', which will brighten the photo. Use it when the photo is too dark to describe the person in the photo
    - 'OK', with which you signal that the photo is fixed and it is possible to describe the person in the photo
</rules>"""

    user_prompt = "What operation should be done on this image?"
    response = ""

    while ai_requests_number < max_ai_requests_number:
        response = await get_ai_response_about_image(user_prompt, system_prompt, image_data["url"])
        print(f"Response from AI about {image_data["url"]}:", response)
        if response == "OK":
            return image_data
        elif response in ["REPAIR", "DARKEN", "BRIGHTEN"]:
            server_response = send_answer_to_server_or_get_image(response+" "+image_data["name"])["message"].split(" ")
            changed_url = False
            for text in server_response:
                if "PNG" in text and "https" in text:
                    image_data["url"] = text
                    name = text.split("/")
                    image_data["name"] = name[-1]
                    changed_url = True
                elif "PNG" in text:
                    url = image_data["url"]
                    url = url.split("/")
                    url.pop(-1)
                    url.append(text)
                    image_data["url"] = "/".join(url)
                    image_data["name"] = text
                    changed_url = True

            if not changed_url:
                system_prompt+=f"\nYour previously performed {response} operation was not a good choice"
            ai_requests_number += 1
        
    return image_data


async def get_ai_response_about_image(user_prompt, system_prompt, url):
    print("Sending image to AI")

    ai_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
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
                            "url": url,
                            "detail": "low"
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
    return ai_response.choices[0].message.content


async def get_ai_response(user_prompt, system_prompt):
    print("Sending prompts to AI")
    ai_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": user_prompt}
        ]
    )
    return ai_response.choices[0].message.content


async def main():
    response = send_answer_to_server_or_get_image("START")
    response = response["message"].split(" ")
    images = []
    urls_number = 0
    url = None
    images_names = []
    for text in response:
        if text[-1] == ".":
            text = text[:-1]

        if text[-1] == ",":
            text = text[:-1]

        if "https" in text and "PNG" in text:
            images.append({"url": text, "name": text.split("/")[-1]})
        elif "https" in text:
            url = text[:-1]
        elif "PNG" in text:
            images_names.append(text)
    
    if url:
        for image_name in images_names:
            images.append({"url": url+"/"+image_name, "name": image_name})
    print(images)

    tasks = []
    for image in images:
        tasks.append(asyncio.create_task(get_right_image(image)))

    repaired_images = await asyncio.gather(*tasks)

    tasks = []
    for repaired_image in repaired_images:
        tasks.append(asyncio.create_task(get_ai_response_about_image("Write a description of the person in the photo in Polish as precisely as possible.", "You are an assistant whose task is to write a description of the person in the photo in the language provided by the user. Focus solely on this task.", repaired_image["url"])))

    descriptions = await asyncio.gather(*tasks)
    print("Descriptions:", descriptions)

    system_prompt = """You are an assistant whose job is to prepare the final description of a person based on his/her description in the user's message.
<rules>.
- You can only reply in Polish
- Focus only on preparing the description of the person
- The given descriptions may include drawings of several people. Return only the description of the person who appears most often
</rules>"""

    user_prompt = ""
    for i in range(0, len(descriptions)):
        user_prompt += str(i)+". "+descriptions[i]+"\n"

    final_description = await get_ai_response(user_prompt, system_prompt)
    print("Final description:", final_description)
    send_answer_to_server_or_get_image(final_description)


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())