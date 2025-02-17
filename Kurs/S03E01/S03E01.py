import json
import asyncio
import os
import requests
import re

from dotenv import load_dotenv
from openai import AsyncOpenAI


def connect_files(keywords):
    report_files = []
    for record in keywords:
        if not "facts" in record["file"]:
            associated_files = []
            associated_files.append(record["file"])
            for associated_record in keywords:
                if associated_record != record:
                    for keyword in record["keywords"]:
                        if keyword in associated_record["keywords"]:
                            associated_files.append(associated_record["file"])
            report_files.append(associated_files)

    return report_files



def get_file_paths(directory):
    if os.path.exists(directory) and os.path.exists(directory+"/facts"):
        files = []

        for file in os.listdir(directory):
            if os.path.splitext(file)[1] == ".txt":
                file_path = os.path.join(directory, file)
                files.append(file_path)

        for file in os.listdir(directory+"/facts"):
            if os.path.splitext(file)[1] == ".txt":
                file_path = os.path.join(directory+"/facts", file)
                files.append(file_path)

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
        "task":"dokumenty",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


async def generate_keywords_for_files(user_prompt, file_path):
    print("Sending prompt to AI")
    system_prompt = '''Based on the text provided by the user, write out in a string the keywords from this text separated by commas in the language of the text provided by the user.
    The list is to consist only of names, sector names and proper names or nicknames of persons appearing in the text, e.g. 'Kowalski, Nowak, Sektor B1'.
    You are not permitted to respond in any other way than by using such a list!'''

    ai_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": user_prompt}
        ]
    )

    results = [x.strip() for x in (ai_response.choices[0].message.content).split(',')]
    return {"file": file_path, "keywords": results}


async def generate_keywords_for_final_answer(user_prompt, data):
    print("Sending prompt to AI")
    system_prompt = f'''You are an assistant whose task is to list as many keywords as possible related to a given text provided by the user. The 'data' section contains additional information about the user's text to help create additional keywords.

<rules>.
- Only answer with a string of keywords containing names, professions and others of this type, e.g. 'Jan Nowak, piekarz, robot, AI'.
- You may only reply in the language of the text provided by the user
- When creating keywords, also use the information provided in the 'data' section
- List as many of these keywords as possible containing all the information mentioned about people (at least 15 keywords), characters, professions, events, places, PROGRAMMING LANGUAGES USED BY PEOPLE, technologies, people's knowledge, e.g. not mentioning that somebody knows JavaScript is a mistake. You must not leave out any such detail, so focus on it as much as you can
- If the user data contains information about the person and in the 'data' section you have information that the person likes a programming language (for example, JavaScript), then not mentioning this is an error. You have to mention it. In your previous answers you still do not include information about individuals and their interests such as programming languages(You answered: Barbara Zawadzka, czujniki dźwięku, nadajnik, analiza odcisków palców, las, obiekt, zielone krzaki, dział śledczy, baza urodzeń, ultradźwiękowy sygnał, obszar zabezpieczony, patrol, incydenty, techniki analizy, bezpieczeństwo, sektor C4). It is a huge mistake
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
        ]
    )

    return ai_response.choices[0].message.content


async def main():
    choice = input("Do you want to reassign phrases for file association? (Y/N or Yes/No): ")
    if choice.lower() == "y" or choice.lower() == "yes":
        tasks = []
        files = get_file_paths("pliki_z_fabryki")
        for file_path in files:
            with open(file_path, 'r') as file:
                tasks.append(asyncio.create_task(generate_keywords_for_files(file.read(), file_path)))

        results = await asyncio.gather(*tasks)

        with open('data.json', 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False)
    elif choice.lower() != "n" and choice.lower() != "no":
        print("Invalid choice!")
        return

    with open('data.json', 'r', encoding='utf-8') as file:
        keywords = json.load(file)

    report_files = connect_files(keywords)
    print("Generated connections between files using keywords:", report_files)

    answer = {}
    pattern = r"sektor_[A-Z]\d"
    for report_file in report_files:
        file_name = report_file[0].split("\\")[-1]
        match = re.search(pattern, file_name)

        with open(report_file[0], 'r') as file:
            text = file.read()
        
        additional_data = ""
        for i in range(1, len(report_file)):
            with open(report_file[i], 'r') as file:
                additional_data += file.read()+"\n"
        
        ai_response = await generate_keywords_for_final_answer(text, additional_data)
        ai_response += ", "+match.group(0).replace("_", " ")
        answer[file_name] = ai_response.replace(".", "")
    
    print("Generated answer:", answer)
    send_answer_to_server(answer)


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())