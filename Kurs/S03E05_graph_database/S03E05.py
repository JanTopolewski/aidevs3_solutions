import asyncio
import json
import os
import requests
import uuid

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from neo4j import GraphDatabase


class Graph_Database_Service:
    def __init__(self, url, username, password, embedding_function, index_name, max_chunk_size, chunk_overlap):
        self.embedding_function = embedding_function
        self.url = url
        self.username = username
        self.password = password

        self.graph_database = Neo4jGraph(
            url=url,
            username=username,
            password=password
        )

        self.create_index_directly(index_name)

        self.vector_storage = Neo4jVector(
            embedding=embedding_function,
            url=url,
            username=username,
            password=password,
            index_name="people",
            graph=self.graph_database
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size, chunk_overlap=chunk_overlap, length_function=len, separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )


    def create_index_directly(self, index_name):
        driver = GraphDatabase.driver(self.url, auth=(self.username, self.password))
        with driver.session() as session:
            session.run(f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS 
            FOR (d:Document) ON (d.embedding)
            OPTIONS {{indexConfig: {{`vector.dimensions`: 1536, `vector.similarity_function`: "cosine"}}}}
            """)
        driver.close()


    def clear_database(self, index_name):
        self.graph_database.query("MATCH (n) DETACH DELETE n;")

        print("Cleared database")


    def search_for_relationships(self, text1, text2, k1, k2, relationship_name):
        doc1, score1 = self.vector_storage.similarity_search_with_relevance_scores(text1, k=k1)[0]
        doc2, score2 = self.vector_storage.similarity_search_with_relevance_scores(text2, k=k2)[0]

        doc1_id = doc1.metadata.get("metadata_id")
        doc2_id = doc2.metadata.get("metadata_id")

        query = f"""MATCH path = shortestPath((d1:Document)-[:{relationship_name}*]-(d2:Document))
    WHERE d1.id = $doc1_id AND d2.id = $doc2_id
    RETURN nodes(path) AS nodes, relationships(path) AS relationships
        """
        print("Searching for path between nodes")

        results = self.graph_database.query(query, {"doc1_id": doc1_id, "doc2_id": doc2_id})

        return results


    def add_node(self, data, id):
        chunks = self.text_splitter.split_text(data)
        if id == None:
            for chunk in chunks:
                id = str(uuid.uuid4())
                embedding = self.embedding_function.embed_query(chunk)

                self.graph_database.query("""
                CREATE (d:Document {
                    id: $id,
                    text: $text,
                    embedding: $embedding,
                    metadata_id: $metadata_id
                })
                """, {
                    "id": id,
                    "text": chunk,
                    "embedding": embedding,
                    "metadata_id": id
                })
        elif len(chunks) > 1:
            print("Not enough ids were given while adding node. Skiping ading")
        else:
            embedding = self.embedding_function.embed_query(chunks[0])

            self.graph_database.query("""
            CREATE (d:Document {
                id: $id,
                text: $text,
                embedding: $embedding,
                metadata_id: $metadata_id
            })
            """, {
                "id": id,
                "text": chunks[0],
                "embedding": embedding,
                "metadata_id": id
            })
        print("Added new node/nodes")


    def create_relationship(self, document1_id, document2_id):
        self.graph_database.query("""
        MATCH (d1:Document {id: $doc1_id}), (d2:Document {id: $doc2_id})
        MERGE (d1)-[:KNOWS]->(d2)
        """, {
            "doc1_id": document1_id,
            "doc2_id": document2_id
        })
        print("Created new relationship")



def send_answer_to_server(answer):
    endpoint = os.getenv("TASKS_ENDPOINT")

    headers = {
        'Content-Type':'application/json'
    }
    data = {
        "task":"connections",
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

    return server_response.json()["reply"]


async def main():
    choice = input("Do you want to add data to graph database? (Y/N or Yes/No): ")
    neo4j = None
    embedding_function = OpenAIEmbeddings(model="text-embedding-3-small", max_retries=5, request_timeout=15, retry_max_seconds=4, retry_min_seconds=1)
    if choice.lower() == "y" or choice.lower() == "yes":
        neo4j = Graph_Database_Service(os.getenv("NEO4J_URL"), os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"), embedding_function, "people", 500, 150)
        neo4j.clear_database("people")

        users = query_database("SELECT * FROM users")
        connections = query_database("SELECT * FROM connections")
        for user in users:
            neo4j.add_node(user["username"], user["id"])

        for connection in connections:
            neo4j.create_relationship(connection["user1_id"], connection["user2_id"])
    elif choice.lower() != "n" and choice.lower() != "no":
        print("Invalid choice!")
        return

    if not neo4j:
        neo4j = Graph_Database_Service(os.getenv("NEO4J_URL"), os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"), embedding_function, "people", 500, 150)

    search_results = neo4j.search_for_relationships("Rafał", "Barbara", 1, 1, "KNOWS")

    nodes = search_results[0].get("nodes", [])
    page_contents = [node.get("text") for node in nodes]
    print("Nodes' path:", page_contents)
    send_answer_to_server(", ".join(page_contents))


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())