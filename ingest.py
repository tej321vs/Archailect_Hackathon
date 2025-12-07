# ingest.py - LOCAL MONGODB
import os, glob, requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# LOCAL MONGODB (NO ATLAS NEEDED)
client = MongoClient("mongodb://localhost:27017/")
db = client["rag_chatbot"]
collection = db["website_docs"]

# DEMO URLs - REPLACE WITH YOUR CHOICE
URLS = [
    "https://docs.streamlit.io/get-started",
    "https://docs.streamlit.io/library/api-reference",
    "https://docs.streamlit.io/deploy"
]

DATA_DIR = "data/pages"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_and_save():
    for i, url in enumerate(URLS):
        print(f"Scraping {url}...")
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style"]): tag.extract()
        text = soup.get_text(separator="\n", strip=True)
        with open(f"{DATA_DIR}/page_{i}.txt", "w", encoding="utf-8") as f:
            f.write(text)

def chunk_text(text, chunk_size=500, overlap=100):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def build_vector_store():
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Clear existing data
    collection.delete_many({})
    
    docs = []
    for path in glob.glob(f"{DATA_DIR}/*.txt"):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        chunks = chunk_text(raw)
        for idx, chunk in enumerate(chunks):
            embedding = embed_model.encode([chunk]).tolist()[0]
            docs.append({
                "content": chunk,
                "source": os.path.basename(path),
                "chunk_id": f"{os.path.basename(path)}_{idx}",
                "embedding": embedding
            })
    
    if docs:
        collection.insert_many(docs)
        print(f"✅ Inserted {len(docs)} chunks into LOCAL MongoDB")
    
    client.close()

if __name__ == "__main__":
    fetch_and_save()
    build_vector_store()
