import json
import asyncio
import requests
import os

from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from dotenv import load_dotenv
import html2text


def save_as_markdown(soup):
    markdown_content = html2text.html2text(str(soup))
    with open('data/output.md', 'w', encoding='utf-8') as file:
        file.write(markdown_content)


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"arxiv",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


async def transcribe_audio(file_path):
    print("Sending audio to Whisper")
    with open(file_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcription


async def modify_audio(url, tag):
    global audio_number
    response = requests.get(url)
    if response.status_code == 200:
        with open("data/audio"+str(audio_number)+".mp3", 'wb') as f:
            f.write(response.content)
        print("Saved audio file")

        transcription = await transcribe_audio("data/audio"+str(audio_number)+".mp3")
        audio_number+=1
        tag.name = 'p'
        tag.string = f'(Zawartość audio: {transcription})'
    else:
        raise ValueError("Error while downloading audio file!")


async def describe_image_via_ai(user_prompt, url):
    print("Sending image to AI")
    system_prompt = "You are an assistant whose task is to describe in Polish language as accurately as possible everything in the given photo including various objects, text, etc. The user will give you an additional caption for the photo in their message which will help you understand the context of the image. Respond only with a description."

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


async def modify_image(user_prompt, url, caption, tag):
    description = await describe_image_via_ai(user_prompt, url)
    tag.name = 'p'
    tag.string = f'(Podpis obrazu: {caption}; Opis obrazu: {description})'


async def download_and_modify_html_data(url, base_url):
    html_content = requests.get(url).text

    soup = BeautifulSoup(html_content, 'html.parser')

    tasks = []

    for a in soup.find_all('a'):
        a.decompose()

    figure_list = soup.find_all('figure')
    audio_list = soup.find_all('audio')

    for figure in figure_list:
        img = figure.find('img')
        figcaption = figure.find('figcaption')
        if img and figcaption:
            src = img.get('src')
            tasks.append(asyncio.create_task(modify_image(f"Describe the given image. Caption of this image: {figcaption.text}", base_url+src, figcaption.text, figure)))

    for audio in audio_list:
        source_tag = audio.find('source')
        src = source_tag.get('src')
        tasks.append(asyncio.create_task(modify_audio(base_url+src, audio)))

    await asyncio.gather(*tasks)

    save_as_markdown(soup)
    print("Saved data to markdown file")


async def get_answer_from_gpt(user_prompt, data):
    print("Sending prompts to AI")
    system_prompt = f'''You are an assistant answering questions accurately based on the data provided by the user.
<objective>.
Answer the questions provided by the user as accurately as possible based on the data provided in the 'data' section. Include your answer in the given json format:
{{
    "01": "krótka odpowiedź w 1 zdaniu",
    "02": "krótka odpowiedź w 1 zdaniu",
    "03": "krótka odpowiedź w 1 zdaniu",
    "04": "krótka odpowiedź w 1 zdaniu",
    ...
}}
</objective>

<rules>.
- Answers to the questions have to be in one sentence and in Polish
- Be sure to use the correct json format, where keys are consecutive task numbers as in the example, and values are the answers to the questions
- The 'Podpis obrazu', 'Opis obrazu' and 'Zawartość audio' sections are in brackets in the data provided. These indicate that there are images or audio files whose descriptions are provided for you to understand
- Make sure that the number in the returned json matches the question number provided by the user
- 'Podpis obrazu' is a caption under the image. It may help you understand the context
- If the answer is not given directly then obtaining it may require the use of your own knowledge to determine places, times and so on, e.g. when a specific element occurring in a particular place is mentioned. Focus on replying perfectly this way using your knowledge!
- Answer questions precisely, including with photo descriptions. If you have a question about something specific, you must always give a concrete description of it, but in one sentence, e.g. in a question about food, include a description of the food, what was in it, what products and ingredients it had, e.g. replace 'ciasta' with 'ciasta z czekoladą'. Therefore, something like this is incorrect: 'Resztki ciasta zostały pozostawione przez Rafała.' and should contain a better description of the cake like 'Resztki ciasta z czekoladą zostały pozostawione przez Rafała.'. This is key to the correct answer
</rules>

<data>
{data}
</data>'''

    ai_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    return ai_response.choices[0].message.content


async def main():
    choice = input("Do you want to process data before answering? (Y/N or Yes/No): ")
    if choice.lower() == "y" or choice.lower() == "yes":
        await download_and_modify_html_data("secret_url", "secret_url")

    elif choice.lower() != "n" and choice.lower() != "no":
        print("Invalid choice!")
        return

    if os.path.exists("data/output.md"):
        questions = requests.get(f"secret_url").text
        with open('data/output.md', 'r', encoding='utf-8') as file:
            response = await get_answer_from_gpt(questions, file.read())
        print("AI repsonse:", response)
        response = json.loads(response)
        
        send_answer_to_server(response)

    else:
        raise FileNotFoundError("You should choose 'Yes' due to the fact that no data has been processed yet!")


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    audio_number = 1
    asyncio.run(main())