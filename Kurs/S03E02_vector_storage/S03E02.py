import json
import asyncio
import os
import requests
import shutil

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


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


    def search_in_vector_storage(self, query, k):
        print("Searching vector storage")
        results = self.vector_storage.similarity_search_with_relevance_scores(
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
        "task":"wektory",
        "apikey": os.getenv("AIDEVS3_API_KEY"),
        "answer": answer
    }

    server_response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    print('Server response: ',server_response.json())


async def main():
    choice = input("Do you want to add embeddings to vector storage collection again? (Y/N or Yes/No): ")
    vector_storage = None
    if choice.lower() == "y" or choice.lower() == "yes":
        vector_storage = Vector_Storage_Collection(OpenAIEmbeddings(model="text-embedding-3-small", max_retries=5, request_timeout=15, retry_max_seconds=4, retry_min_seconds=1), "vector_storage", "Reports", True)
        
        if os.path.exists("pliki_z_fabryki/weapons_tests/do-not-share"):
            tasks = []
            for item in os.listdir("pliki_z_fabryki/weapons_tests/do-not-share"):
                file_path = os.path.join("pliki_z_fabryki/weapons_tests/do-not-share", item)
                with open(file_path, 'r', encoding='utf-8') as file:
                    tasks.append(asyncio.create_task(vector_storage.add_data_to_vector_storage(file.read(), 800, 350, {"date": os.path.splitext(item)[0].replace("_", "-"), "file_path": file_path})))

            await asyncio.gather(*tasks)
        else:
            raise FileNotFoundError("Could not find files' directory")
    elif choice.lower() != "n" and choice.lower() != "no":
        print("Invalid choice!")
        return

    if not vector_storage:
        vector_storage = Vector_Storage_Collection(OpenAIEmbeddings(model="text-embedding-3-small", max_retries=5, request_timeout=15, retry_max_seconds=4, retry_min_seconds=1), "vector_storage", "Reports", False)

    result = vector_storage.search_in_vector_storage("W raporcie, z którego dnia znajduje się wzmianka o kradzieży prototypu broni?", 1)

    print("Result from vector storage:", result)
    doc, score = result[0]
    send_answer_to_server(doc.metadata.get("date"))
    

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())