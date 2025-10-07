from services.rag_service import RAGService

class TutorAgent:
    def __init__(self):
        self.rag = RAGService()

    def generate_answer(self, query: str):
        response = self.rag.retrieve_and_generate(query)
        return {"query": query, "answer": response}
