import os
import requests
import json
from ollama import chat
import asyncio

def read_file(path):
    with open(path, "r") as file:
        data = file.readlines()
        for i in data:
            i = i.replace("\n", "")
    return data

def save_text_data(path, text):
    with open(path, 'w') as file:
        file.write(text)

def get_text_data(url, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    response = requests.get(url)
    print("Received data:\n", response.text)
    save_text_data(file_path, response.text)
    formatted_data = read_file(file_path)
    return formatted_data

def send_answer_to_server(answer):
    endpoint = 'secret_endpoint'

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"CENZURA",
        "apikey": "secret_apikey",
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())

async def get_answer_from_ollama(system_prompt, text):
    response = chat(
        model = "gemma2:2b",
        messages = [
            {'role':'system', 'content': system_prompt},
            {'role':'user', 'content': text}
        ],
        format = "json"
    )
    print("AI's answer: \n",response['message']['content'])
    print(response)
    return response['message']['content']

async def main():
    data = get_text_data('secret_url', 'sensitive_data.txt')

    system_prompt = '''You are an assistant whose task is to convert data such as names + surnames, street names + house numbers, city names, and ages of people into the word "CENZURA".
<rules>
- Just return the processed sentence in place of three dots in the given json format {"answer":"..."}.
- Remember that if the name is next to the surname or the name of the street and the house number are next to each other, only one word "CENZURA" must be inserted in their place
- Do not remove important abbreviations such as "ul.", words 'ulica' or the characters '.', ',', etc. Replace only the names of streets, but not the word 'ulica' or 'ul.'.
- Remember to convert data such as names + surnames, street names + house numbers, city names, and ages of people into the word "CENZURA". That's the most  important thing
- A common mistake is not replacing the city name with the word 'CENZURA'. You must not make this mistake
- Don't add characters lika ',' after the word 'CENZURA'. You are not allowed to perform any other operations on the given text (like deleting words 'ulica', 'ul.' or adding character like ',') except replacing the words with the word "CENZURA"
</rules>

<examples>
USER: Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie, ul. Akacjowa 7. Wiek: 27 lat.
AI: {"answer":"Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA, ul. CENZURA. Wiek: CENZURA lat."}

USER: Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie na ul. Akacjowej 7. Ma 27 lat.
AI: {"answer":"Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA na ul. CENZURA. Ma CENZURA lat."}

USER: Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie na ulicy Akacjowej 7. Wiek: 27 lat.
AI: {"answer":"Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA na ulicy CENZURA. Wiek: CENZURA lat."}

USER: Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie przy ulicy Akacjowej 7. Wiek: 27 lat.
AI: {"answer":"Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA przy ulicy CENZURA. Wiek: CENZURA lat."}

USER: Informacje o podejrzanym: Wojciech Górski. Przebywa we Wrocławiu przy ul. Akacjowej 7. Wiek: 32 lata.
AI: {"answer":"Informacje o podejrzanym: CENZURA. Przebywa we CENZURA przy ul. CENZURA. Wiek: CENZURA lata."}
</examples>'''

    final_data = []
    for i in data:
        final_data.append(json.loads(await get_answer_from_ollama(system_prompt, i))['answer'])
    send_answer_to_server('\n'.join(final_data))

if __name__ == "__main__":
    asyncio.run(main())