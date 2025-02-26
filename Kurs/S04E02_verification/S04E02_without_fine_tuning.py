import asyncio
import json
import os
import requests

from dotenv import load_dotenv
from openai import AsyncOpenAI


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"research",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


async def get_response_from_ai(system_prompt, user_prompt):
    print("Sending prompt to AI")
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
    with open('lab_data/correct.txt', 'r') as file:
        correct_data = file.read()

    with open('lab_data/incorrect.txt', 'r') as file:
        incorrect_data = file.read()

    with open('lab_data/verify.txt', 'r') as file:
        data_for_verification = file.read()

    system_prompt = f"""You are an assistant whose job is to return the correct index numbers of the research results given by the user.

<rules>.
- Answer only with indexes in the format: 01, 02, 03,....
- In the 'correct_data' section, the correct research results are placed on each line
- In the 'incorrect_data' section placed on each line are incorrect research results
- The user will give you different results in the format:
    01=1, 2, 3, 4
    02=5, 78, 45, 67
The index of a given result is always placed before the '=' sign. You need to find some relationship between the elements in the correct_data section and the relationship between the elements in the incorrect_data section. Compare the characters, the differences between the numbers, their arrangement, etc. Then find out which of the data from the user can be assigned to the correct_data section, as they meet its assumptions
- 
</rules>

<correct_data>
{correct_data}
</correct_data>

<incorrect_data>
{incorrect_data}
</incorrect_data>"""

    ai_response = await get_response_from_ai(system_prompt, data_for_verification)
    print("Response from AI:", ai_response)
    send_answer_to_server(ai_response.split(", "))


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())