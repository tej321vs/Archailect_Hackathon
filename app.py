import streamlit as st
import os
import numpy as np
import requests
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

# LOCAL MONGODB
client = MongoClient("mongodb://localhost:27017/")
db = client["rag_chatbot"]
collection = db["website_docs"]

@st.cache_resource
def load_components():
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return embed_model, collection

def vector_search_local(query, embed_model, collection, k=4):
    docs = list(collection.find({}, {"content": 1, "embedding": 1}).limit(100))
    if not docs:
        return []
    
    contents = [doc["content"] for doc in docs]
    embeddings = np.array([doc["embedding"] for doc in docs])
    
    q_emb = embed_model.encode([query])
    similarities = cosine_similarity(q_emb, embeddings)[0]
    top_indices = np.argsort(similarities)[-k:][::-1]
    
    return [contents[i] for i in top_indices]

def call_ollama(prompt):
    """FREE Local LLM - No OpenAI needed"""
    response = requests.post('http://localhost:11434/api/generate', 
                           json={
                               'model': 'llama3.2',
                               'prompt': prompt,
                               'stream': False
                           })
    return response.json()['response']

def main():
    st.title("🗂️ FREE Local RAG Chatbot (Ollama + MongoDB)")
    
    embed_model, collection = load_components()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.sidebar.header("Settings")
    top_k = st.sidebar.slider("Top K chunks", 2, 8, 4)
    
    # Show chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask about Streamlit docs..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Searching MongoDB + Ollama..."):
                docs = vector_search_local(prompt, embed_model, collection, top_k)
                if not docs:
                    st.error("❌ No data! Run `python ingest.py` first.")
                else:
                    context = "\n\n".join(docs[:3])
                    rag_prompt = f"""Context from website:
{context}

Question: {prompt}

Answer using ONLY the context above. If not found, say "Not in my knowledge base."."""
                    
                    answer = call_ollama(rag_prompt)
                    st.markdown(answer)
        
        st.session_state.messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
