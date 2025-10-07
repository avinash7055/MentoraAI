import random
from services.rag_service import RAGService
from services.llm_service import LLMService

class QuizAgent:
    """
    Handles MCQ generation, quiz delivery, and answer evaluation.
    """

    def __init__(self):
        self.rag = RAGService()
        self.llm = LLMService()

    def generate_quiz(self, topic: str, num_questions: int = 5):
        """
        Create UPSC-style MCQs for a given topic using context documents.
        """
        docs = self.rag.collection.query(query_texts=[topic], n_results=3)
        context = "\n".join(sum(docs["documents"], []))

        prompt = f"""
        You are an expert UPSC question setter.
        Using the following notes, create {num_questions} MCQs with 4 options (A-D)
        and specify the correct answer key at the end.

        Context:
        {context}

        Output JSON in this format:
        [
          {{
            "question": "...",
            "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
            "answer": "B"
          }}
        ]
        """

        result = self.llm.generate_text(prompt)
        return {"topic": topic, "quiz": result}

    def evaluate_quiz(self, questions: list, user_answers: list):
        """
        Compare user answers with the correct answers and calculate score.
        """
        correct = 0
        for i, q in enumerate(questions):
            if i < len(user_answers) and user_answers[i].strip().upper() == q["answer"].strip().upper():
                correct += 1
        score = round((correct / len(questions)) * 100, 2)
        return {"score_percent": score, "correct": correct, "total": len(questions)}
