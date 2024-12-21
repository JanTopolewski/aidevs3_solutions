import requests
from openai import AsyncOpenAI
import json
import asyncio

client = AsyncOpenAI(api_key = "secret_apikey")

def get_data_as_json():
    with open("data.txt", "r") as file:
        data = file.readlines()
        result = json.loads("".join(map(str, data)))
        return result

async def send_answer_to_server(answer):
    endpoint = 'secret_endpoint'

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"JSON",
        "apikey": "secret_apikey",
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())

async def get_answer_from_gpt(question):
    system_prompt = '''You are a helpful assistant that answers as short as possible.
<objective>
- you have to answer the given question as short as possible in English
</objective>
<rules>
- Answer has to be in English. Answer only with letters from that language.
- Answer has to be as short as possible
- respond only with text, for example: Warsaw
</rules>'''

    ai_response = await client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = [
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": question}
        ]
    )
    return ai_response.choices[0].message.content


async def check_answers(json_data):
    for i in json_data['test-data']:
        if i['answer'] != eval(i['question']):
            i['answer'] = eval(i['question'])
        if 'test' in i:
            i['test']['a'] = await get_answer_from_gpt(i['test']['q'])

    print('Result: ',json_data)
    await send_answer_to_server(json_data)
            

async def main():
    json_data = get_data_as_json()
    await check_answers(json_data)

if __name__ == "__main__":
    asyncio.run(main())