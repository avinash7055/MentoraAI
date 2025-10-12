import os
import uuid
import pdfplumber
import chromadb
from sentence_transformers import SentenceTransformer

PDF_DIR = "./data/ncert/"
CHROMA_DIR = "./data/chroma"

def main():
    print("🚀 Starting NCERT PDF ingestion...\n")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    coll = client.get_or_create_collection("ncert_corpus")

    total_docs, total_chunks = 0, 0

    for file in os.listdir(PDF_DIR):
        if not file.endswith(".pdf"):
            continue

        path = os.path.join(PDF_DIR, file)
        print(f"📘 Processing file: {file}")

        try:
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue

                    text = text.strip()
                    chunks = [text[j:j+800] for j in range(0, len(text), 800)]

                    print(f"  🧩 Page {i+1}/{len(pdf.pages)} — {len(chunks)} chunks")

                    try:
                        embs = model.encode(chunks)
                        ids = [str(uuid.uuid4()) for _ in chunks]
                        meta = [{"book": file, "page": i+1}] * len(chunks)

                        coll.add(
                            documents=chunks,
                            embeddings=embs.tolist(),
                            metadatas=meta,
                            ids=ids
                        )
                        total_chunks += len(chunks)

                    except Exception as e:
                        print(f"  ❌ Error embedding page {i+1}: {e}")

            total_docs += 1
            print(f"✅ Finished {file}\n")

        except Exception as e:
            print(f"❌ Failed to process {file}: {e}\n")

    print(f"✅ All done — {total_docs} PDFs processed, {total_chunks} chunks embedded.\n")
    print(f"📦 ChromaDB stored at: {os.path.abspath(CHROMA_DIR)}")

if __name__ == "__main__":
    main()
