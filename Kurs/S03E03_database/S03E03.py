import json
import os
import asyncio
import requests

from dotenv import load_dotenv
from openai import AsyncOpenAI


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"database",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())



def query_database(query):
    print("Sending query to database")
    endpoint = os.getenv("DATABASE_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"database",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "query": query
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print("Database's response:",json.dumps(server_response.json()["reply"], indent=4))
    return json.dumps(server_response.json()["reply"], indent=4)


async def generate_query(user_prompt, users_table, datacenters_table, connections_table):
    print("Sending prompt to AI")
    system_prompt = f'''You are the assistant responsible for managing the mysql database.
<rules>.
- You must design a database query according to the specified structure in the database section following user requirements
- The names of the tags in the database section are the names of the tables whose structure they describe
- You may only respond with the given query
- You must not add any other character
</rules>

<database>
    <users>
        {users_table}
    </users>
    <datacenters>
        {datacenters_table}
    </datacenters>
    <connections>
        {connections_table}
    </connections>
</database>'''

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
    users_table = query_database("desc users")
    datacenters_table = query_database("desc datacenters")
    connections_table = query_database("desc connections")

    query = await generate_query("Które aktywne datacenter (DC_ID) są zarządzane przez pracowników, którzy są na urlopie (is_active=0)", users_table, datacenters_table, connections_table)
    
    print("Generated query:", query)

    results = json.loads(query_database(query))
    ids = []
    for result in results:
        ids.append(int(result["dc_id"]))
    
    send_answer_to_server(ids)


if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())