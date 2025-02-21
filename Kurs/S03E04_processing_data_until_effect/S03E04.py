import requests
import asyncio
import os
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"loop",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


def query_server(url, query):
    endpoint = url

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "query": query
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    return server_response.json()["message"].replace(" ", ", ")


def download_data(url):
    response = requests.get(url)
    response.raise_for_status()

    with open('data.txt', 'w', encoding='utf-8') as file:
        file.write(response.text)

    print("Dowloaded data")
    return response.text


def replace_polish_letters(text):
    for polish_letter, normal_letter in polish_letters.items():
        text = text.replace(polish_letter, normal_letter)
    return text


async def call_ai(system_prompt, user_prompt):
    print("Sending prompt to AI")

    ai_response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    return ai_response.choices[0].message.content


async def main():
    max_ai_requests_number = 20
    ai_requests_number = 0
    data = download_data("secret_endpoint")
    server_replies = ""
    last_city = ""

    while ai_requests_number < max_ai_requests_number:
        system_prompt = f'''You are an assistant whose job it is to get an answer to the user's question.
You have to decide to search the server to obtain the data needed for the answer.
In the "additional_data" section you have additional information to help you target what questions you should ask the server, and in the "server_replies" section you have the data you pulled from the server earlier(Before the colon, the query is listed, and after the colon, its result)

<rules>.
- You may only reply in json format
- You have two response options:
    - {{"NAME": "..."}} will return you the cities where the person with the given name or nickname has stayed
    - {{"CITY": "..."}} will return you the persons who have stayed in the given city
- If the data you receive from the server is empty or marked as restricted, you must try to search for some other name or city
- Searching directly for the name you are looking for may not give you an answer. Then try to arrive at the answer by searching for other names or cities and try to deduce the answer from these afterwards, e.g you always tried to search the same name: AI's response:
{{"NAME": "BARBARA ZAWADZKA"}}
Server's answer: [**RESTRICTED, DATA**]
AI's response: {{"NAME": "BARBARA"}}
Server's answer: [**RESTRICTED, DATA**]
AI's response: {{"NAME": "BARBARA"}}
Server's answer: [**RESTRICTED, DATA**]
AI's response: {{"NAME": "BARBARA"}}
Server's answer: [**RESTRICTED, DATA**]
AI's response: {{"NAME": "BARBARA"}}
Server's answer: [**RESTRICTED, DATA**]
You should try searching for other name to find answer(once you have searched for Barbara, search for other city or name). Searching for the same name or city again is a mistake. Don't do it!
- **Data you have already asked for once will not change, so do not ask for it again**
- Search only for first names, not surnames
- All city names, peoples' names or answers must be returned without Polish characters and in one word
- Remember to correctly assign names to the 'NAME' category and cities to the 'CITY' category. Names such as 'Azazel' should be assigned to the 'NAME' category and searched. Remeber that 'Adam' and 'Gabriel' are names, not cities. Assign a category based on your knowledge of Poland
- You can always search for just one word, but aim for all cities and people found eventually. If something has already been searched for then do not search for it again, as you have already received data about it in the 'server_replies' section. Focus on searching every town or person you have been given, but without repetition. This is very important!
- You are not allowed to repeat a query you have made before
</rules>

<additional_data>
{data}
</additional_data>

<server_replies>
{server_replies}
</server_replies>
'''

        response = await call_ai(system_prompt, "W jakim mieście znajduje się Barbara?")
        response = response.upper()
        print("AI's response:", response)

        if "CITY" in response:
            response = json.loads(response)
            persons = query_server("secret_endpoint", replace_polish_letters(response["CITY"].split(" ")[0]))
            print("Server's answer:", persons)
            if persons.split(", ")[-1] == "BARBARA":
                send_answer_to_server(replace_polish_letters(response["CITY"].split(" ")[0]))
                break
            server_replies += f"- {replace_polish_letters(response["CITY"].split(" ")[0])}: {persons}\n"
        elif "NAME" in response:
            response = json.loads(response)
            places = query_server("secret_endpoint", replace_polish_letters(response["NAME"].split(" ")[0]))
            print("Server's answer:", places)
            server_replies += f"- {replace_polish_letters(response["NAME"].split(" ")[0])}: {places}\n"
            last_city = places.split(", ")[-1]
        ai_requests_number += 1

    if ai_requests_number >= max_ai_requests_number:
        send_answer_to_server(last_city)


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    polish_letters = {
        'Ą': 'A',
        'Ć': 'C',
        'Ę': 'E',
        'Ł': 'L',
        'Ń': 'N',
        'Ó': 'O',
        'Ś': 'S',
        'Ź': 'Z',
        'Ż': 'Z'
    }
    asyncio.run(main())