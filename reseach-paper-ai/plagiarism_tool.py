from langchain_core.tools import tool
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

previous_papers = []

@tool
def plagiarism_check(new_paper_text: str) -> dict:
    """
    Checks plagiarism by comparing new paper with previous papers.
    Returns similarity scores.
    """
    if not previous_papers:
        return {"message": "No previous papers to compare. 0% plagiarism detected."}

    corpus = previous_papers + [new_paper_text]
    vectorizer = TfidfVectorizer().fit_transform(corpus)
    similarity_matrix = cosine_similarity(vectorizer[-1], vectorizer[:-1])
    max_similarity = similarity_matrix.max()
    return {
        "max_similarity_score": round(float(max_similarity * 100), 2),
        "plagiarism_detected": max_similarity > 0.3,  # Threshold can be adjusted
    }
