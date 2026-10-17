from typesafe_sdk import TypeSafeClient, Noul
from dotenv import load_dotenv

load_dotenv()

client = TypeSafeClient()


def jev_scoring(user_query, chunks, top_k=3):
    chunks_mapping = {f"C{i+1}": j for i, j in enumerate(chunks)}
    state = {"query": user_query, "documents": chunks_mapping}
    questions = {
        f"C{i+1}": Noul(
            instructions=f"Does document C{i+1} helps in answering the query user asked?"
        )
        for i in range(len(chunks))
    }

    response = client.system_one(state=state, questions=questions)

    scored_docs = [(j, response.answers[f"C{i+1}"].noul) for i, j in enumerate(chunks)]

    ranked = sorted(scored_docs, key=lambda x: x[1], reverse=True)
    return [{"document": doc, "score": float(score)} for doc, score in ranked[:top_k]]
