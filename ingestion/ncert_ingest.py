import os, pdfplumber, uuid
from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

PDF_DIR = "./data/ncert/"
CHROMA_DIR = "./data/chroma"

def main():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))
    coll = client.get_or_create_collection("ncert_corpus")

    for file in os.listdir(PDF_DIR):
        if not file.endswith(".pdf"): continue
        path = os.path.join(PDF_DIR, file)
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue
                chunks = [text[j:j+800] for j in range(0, len(text), 800)]
                embs = model.encode(chunks)
                ids = [str(uuid.uuid4()) for _ in chunks]
                meta = [{"book": file, "page": i}] * len(chunks)
                coll.add(documents=chunks, embeddings=embs.tolist(), metadatas=meta, ids=ids)
    client.persist()
    print("✅ NCERT PDFs embedded.")
