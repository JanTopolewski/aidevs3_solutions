from openai import AsyncOpenAI
import asyncio
import requests
import re
from bs4 import BeautifulSoup

client = AsyncOpenAI(api_key = "secret_api_key")

async def get_element_text(url):
    response = requests.get(url)
    html_content = response.content

    soup = BeautifulSoup(html_content, "html.parser")

    element = soup.find(id='human-question')

    if element:
        text_content = element.get_text()
        text_content = text_content.replace("Question:", "")
        print("Text inside the element: ", text_content)
        return text_content
    else:
        print("Some problem occurred in finding the element!")
        return None

async def send_answer(model_response, url):
    print("Response: ",model_response)
    x = re.findall("^\d{1,4}$", model_response)

    if x:
        model_response = int(model_response)
        payload = {
            'username':'tester',
            'password':'574e112a',
            'answer':model_response
        }

        server_response = requests.post(url, data=payload)

        print("Server response: ", server_response.text)
    else:
        print("The response is false")

async def get_model_response(prompt):
    response = await client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = [
            {"role" : "system", "content" : '''You are a helpful assistant that answers as short as possible.
            <rules>
                -Your answer has to be an integer
                -Your answer can only contain digits. You are not allowed to respond with any other character.
            </rules>'''},
            {"role" : "user", "content" : prompt}
        ]
    )

    return response.choices[0].message.content

async def main():
    user_prompt = "Answer the question: "+str(await get_element_text("secret_endpoint"))
    model_text_response = await get_model_response(user_prompt)
    await send_answer(model_text_response, "secret_endpoint")

if __name__ == "__main__":
    asyncio.run(main())