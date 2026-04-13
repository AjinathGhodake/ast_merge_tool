import math

documents = [
    "FastAPI is a modern Python web framework for building APIs.",
    "Transformers use self-attention to process sequences in parallel.",
    "PostgreSQL is a relational database system.",
    "LangGraph helps build deterministic agent workflows.",
]


def embed(text: str) -> list[float]:
    # fake deterministic embedding
    return [len(text), sum(ord(c) for c in text) % 1000]


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b)


def answer_question(question: str, documents: list[str]) -> str:
    q_emb = embed(question)

    scored = []
    for doc in documents:
        score = cosine_similarity(q_emb, embed(doc))
        scored.append((score, doc))

    scored.sort(reverse=True)

    top_score, top_doc = scored[0]

    if top_score < 0.8:
        return "I don’t know based on the provided context"

    context = "\n".join(doc for _, doc in scored[:2])

    return f"""
Answer using ONLY the context below.

Context:
{context}

Answer:
{top_doc}
""".strip()


print(answer_question("What is FastAPI?", documents))
print(answer_question("What is Transformers?", documents))
# print(answer_question("What is PostgreSQL?", documents))
# print(answer_question("What is LangGraph?", documents))
# print(
#     answer_question(
#         "What is the answer to life, the universe, and everything?", documents
#     )
# )
# print(
#     answer_question(
#         "What is the meaning of life, the universe, and everything?", documents
#     )
# )
# print(
#     answer_question(
#         "What is the meaning of life, the universe, and everything?", documents
#     )
# )
