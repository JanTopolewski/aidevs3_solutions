import asyncio
import os
import requests
import json
import shutil
import base64

import PyPDF2
from dotenv import load_dotenv
from openai import AsyncOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import fitz
from PIL import Image


class Vector_Storage_Collection:
    def __init__(self, embedding_function, directory, collection_name, clearing):
        self.embedding_function  = embedding_function
        self.directory = directory
        self.collection_name = collection_name

        if os.path.exists(self.directory):
            if len(os.listdir(self.directory)) > 0 and clearing:
                for item in os.listdir(self.directory):
                    item_path = os.path.join(self.directory, item)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                print("Vector storage directory cleaned successfully")
            
            self.vector_storage = Chroma(
                collection_name=self.collection_name, embedding_function=self.embedding_function, persist_directory=self.directory
            )
            print("Connected to vector storage")
        else:
            raise FileNotFoundError(f"Vector storage directory {self.directory} does not exist")


    async def search_in_vector_storage(self, query, k):
        print("Searching vector storage")
        results = await self.vector_storage.asimilarity_search_with_relevance_scores(
            query, k
        )

        return results


    async def add_data_to_vector_storage(self, data, max_chunk_size, chunk_overlap, metadata):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size, chunk_overlap=chunk_overlap, length_function=len, separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )

        chunks = text_splitter.split_text(data)

        await self.vector_storage.aadd_texts(texts=chunks, metadatas=[metadata]*len(chunks))
        print("Added some documents to vector storage")


def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"notes",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())
    return server_response.json()


async def get_text_from_pdf(file_path, pages):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text+"\n"+await find_and_interpret_images_in_pdf(file_path, "images", pages)


async def find_and_interpret_images_in_pdf(file_path, output_folder, page_numbers):
    pdf_document = fitz.open(file_path)
    for page_number in page_numbers:
        page = pdf_document[page_number]
        image_list = page.get_images()

        if image_list:
            pix = page.get_pixmap()
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image_filename = f"{output_folder}/page_{page_number+1}.png"
            image.save(image_filename)

    pdf_document.close()

    tasks = []
    for file in os.listdir(output_folder):
        file_path = os.path.join(output_folder, file)
        tasks.append(asyncio.create_task(get_ai_response_about_image("You are an assistant whose job is to extract all the text from the image. Respond only with that text.", "Extract text from my image", file_path)))

    results = await asyncio.gather(*tasks)
    return "\n".join(results)


async def get_ai_response_about_image(system_prompt, user_prompt, image_path):
    print("Sending image to AI")

    ai_response = await client.chat.completions.create(
        model = "gpt-4o-mini",
        temperature = 0.1,
        messages = [
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
                            "url": f"data:image/jpeg;base64,{await encode_image(image_path)}"
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
        

async def get_answer_from_gpt(system_prompt, user_prompt, model):
    print("Getting answer from AI")

    ai_response = await client.chat.completions.create(
        model = model,
        temperature = 0.1,
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ]
    )
    return ai_response.choices[0].message.content


async def answer_question(question, question_number, vector_storage: Vector_Storage_Collection, searching, model):
    if searching:
        system_prompt = f"You are an assistant who must extract some keywords from a given question. Respond only with the keywords."
        keywords = await get_answer_from_gpt(system_prompt, question, "gpt-4o-mini")
        print("Extracted keywords:", keywords)
        search_results = await vector_storage.search_in_vector_storage(keywords, 5)
        data = ""
        for document, score in search_results:
            data += document.page_content+"\n"
    else:
        documents = vector_storage.vector_storage.get()["documents"]
        data = "\n".join(documents)

    system_prompt = f"""You are an assistant who must, based on the data in the data section(use also your knowledge in order to get information), answer the user's question as briefly as possible. The answer must be in Polish. The answer can even be just one word, but do not add any dots at the end of the response.

    <data>
    {data}
    </data>

    <rules>
    - The main character of the text given to you is a time traveler. Based on the facts mentioned in the notes given to you by him, relate them to your own knowledge(e.g., about the dates of events) and answer the questions.
    - Some city's names may be incorrect. You have to use your knowledge and information from the data section to answer properly(e.g. Lunary is incorrect name of the city and should be replaced by Lubawa).
    - You must use your own knowledge, such as from the books mentioned in the text using siglum. It is very important to use data from those sources. Remember that dates can be given relatively e.g. using words such as: tomorrow, the day after tomorrow. Take this into account when answering with dates by giving a date a day later or two later, etc.
    </rules>
    Always check that you have met the rules given. This is very important to correct dates, city names and search for knowledge in other sources like books mentioned!"""

    if question_number == "01":
        system_prompt += "Years 2020, 2021, 2022, 2023, 2024, 2025, 2030, 2035 and 2356 are not a right answer. Give another year (You can't use the ones mentioned before). Hint: 'uwzględnij wszystkie fakty podane w tekście, w szczególności odwołania do wydarzeń. Musisz na podstawie własnej wiedzy stwierdzić w jakim roku było dane wydarzenie takie jak stworzenie danych modeli językowych, gdyż to oznacza, że w danym roku był bohater'"
    ai_response = await get_answer_from_gpt(system_prompt, question, model)
    return {question_number: ai_response}


async def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def main():
    choice = input("Do you want to read a pdf file and save data to vector storage? (Y/N or Yes/No): ")
    vector_storage = None
    if choice.lower() == "y" or choice.lower() == "yes":

        vector_storage = Vector_Storage_Collection(OpenAIEmbeddings(model="text-embedding-3-small", max_retries=5, request_timeout=15, retry_max_seconds=4, retry_min_seconds=1), "vector_storage", "Notes", True)
        
        if os.path.exists("notatnik-rafala.pdf"):
            text = await get_text_from_pdf("notatnik-rafala.pdf", pages=[19-1])
            print(text)
            await vector_storage.add_data_to_vector_storage(text, 800, 350, None)
        else:
            raise FileNotFoundError("Could not find files' directory")
    elif choice.lower() != "n" and choice.lower() != "no":
        print("Invalid choice!")
        return

    if not vector_storage:
        vector_storage = Vector_Storage_Collection(OpenAIEmbeddings(model="text-embedding-3-small", max_retries=5, request_timeout=15, retry_max_seconds=4, retry_min_seconds=1), "vector_storage", "Notes", False)

    questions = requests.get(f"secret_url")
    questions.raise_for_status()
    questions_json = questions.json()

    tasks = []
    for index, question in questions_json.items():
        print(index, question)
        tasks.append(asyncio.create_task(answer_question(question, index, vector_storage, True, "gpt-4o")))

    answers = await asyncio.gather(*tasks)

    merged_answers = {}
    for json_file in answers:
        for key, value in json_file.items():
            merged_answers[key] = value
    
    print("Answers:", json.dumps(merged_answers))

    response_code = send_answer_to_server(merged_answers)["code"]
    if response_code != 200:
        tasks = []
        for index, question in questions_json.items():
            print(index, question)
            tasks.append(asyncio.create_task(answer_question(question, index, vector_storage, False, "gpt-4o")))

        answers = await asyncio.gather(*tasks)

        merged_answers = {}
        for json_file in answers:
            for key, value in json_file.items():
                merged_answers[key] = value
        
        print("Answers:", json.dumps(merged_answers))
        send_answer_to_server(merged_answers)



if __name__ == "__main__":
    load_dotenv()
    client = AsyncOpenAI()
    asyncio.run(main())