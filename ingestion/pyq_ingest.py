import csv, uuid
from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CSV_PATH = "./data/pyqs.csv"
CHROMA_PATH = "./data/chroma"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def main():
    model = SentenceTransformer(MODEL_NAME)
    client = Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_PATH))
    collection = client.get_or_create_collection("pyq_corpus")

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row.get("question")
            answer = row.get("answer")
            subject = row.get("subject")
            text = f"Q: {question}\nA: {answer}"
            embedding = model.encode([text])[0].tolist()
            collection.add(
                ids=[str(uuid.uuid4())],
                documents=[text],
                metadatas=[{"subject": subject, "year": row.get("year")}],
                embeddings=[embedding]
            )
    client.persist()
    print("✅ PYQ corpus ingested successfully!")

if __name__ == "__main__":
    main()
