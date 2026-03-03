from langchain_core.tools import tool
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

previous_papers = []

@tool
def add_paper_to_corpus(paper_text: str) -> dict:
    """
    Add a paper to the comparison corpus for plagiarism checking.
    
    Args:
        paper_text: The text content of the paper to add
        
    Returns:
        Confirmation message with corpus size
    """
    if paper_text and len(paper_text) > 50:
        previous_papers.append(paper_text)
        return {
            "message": f"Paper added to corpus. Total papers: {len(previous_papers)}",
            "corpus_size": len(previous_papers)
        }
    return {"message": "Paper text too short to add to corpus."}

@tool
def get_corpus_size() -> dict:
    """
    Get the current size of the comparison corpus.
    
    Returns:
        Current number of papers in the corpus
    """
    return {
        "corpus_size": len(previous_papers),
        "message": f"Current corpus contains {len(previous_papers)} papers"
    }

@tool
def clear_corpus() -> dict:
    """
    Clear all papers from the comparison corpus.
    
    Returns:
        Confirmation message
    """
    global previous_papers
    previous_papers = []
    return {"message": "Corpus cleared. No papers to compare against."}

@tool
def plagiarism_check(new_paper_text: str) -> dict:
    """
    Checks plagiarism by comparing new paper with previous papers.
    Returns similarity scores.
    """
    if not previous_papers:
        return {
            "message": "No previous papers to compare. 0% plagiarism detected.",
            "max_similarity_score": 0.0,
            "plagiarism_detected": False
        }

    corpus = previous_papers + [new_paper_text]
    vectorizer = TfidfVectorizer().fit_transform(corpus)
    similarity_matrix = cosine_similarity(vectorizer[-1], vectorizer[:-1])
    max_similarity = similarity_matrix.max()
    return {
        "max_similarity_score": round(float(max_similarity * 100), 2),
        "plagiarism_detected": max_similarity > 0.3,  # Threshold can be adjusted
        "papers_compared": len(previous_papers)
    }
