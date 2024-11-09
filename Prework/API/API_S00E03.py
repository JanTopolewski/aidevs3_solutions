import requests
import json

scraping_url = 'https://poligon.aidevs.pl/dane.txt'
response = requests.get(scraping_url)

response = response.text.split()
print(response)

api_url = 'secret_endpoint'

headers = {
    'Content-Type':'application/json'
}
data = {
    "task":"POLIGON",
    "apikey": "secret_apikey",
    "answer": response
}

api_response = requests.post(api_url, headers=headers, data=json.dumps(data))

print(api_response.json())