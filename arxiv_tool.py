# # Step1: Access arXiv using URL
# import requests
# import xml.etree.ElementTree as ET
# from langchain_core.tools import tool
# from bs4 import BeautifulSoup


# def search_arxiv_papers(topic: str, max_results: int = 5) -> dict:
#     query = "+".join(topic.lower().split())
#     for char in list('()" '):
#         if char in query:
#             print(f"Invalid character '{char}' in query: {query}")
#             raise ValueError(f"Cannot have character: '{char}' in query: {query}")
#     url = (
#             "http://export.arxiv.org/api/query"
#             f"?search_query=all:{query}"
#             f"&max_results={max_results}"
#             "&sortBy=submittedDate"
#             "&sortOrder=descending"
#         )
#     print(f"Making request to arXiv API: {url}")
#     resp = requests.get(url)
    
#     if not resp.ok:
#         print(f"ArXiv API request failed: {resp.status_code} - {resp.text}")
#         raise ValueError(f"Bad response from arXiv API: {resp}\n{resp.text}")
    
#     data = parse_arxiv_xml(resp.text)
#     return data
# # --------------------------
# # IEEE Xplore search
# # --------------------------
# def search_ieee_papers(topic: str, max_results: int = 5) -> dict:
#     query = "+".join(topic.split())
#     url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={query}"
#     print(f"Scraping IEEE Xplore for topic: {topic}")
#     headers = {"User-Agent": "Mozilla/5.0"}
#     resp = requests.get(url, headers=headers)
#     if not resp.ok:
#         raise ValueError(f"IEEE Xplore request failed: {resp.status_code}")
    
#     # Parse papers using BeautifulSoup
#     soup = BeautifulSoup(resp.text, "html.parser")
#     # IEEE search results are often dynamically loaded via JS
#     # We'll attempt to parse JSON embedded in the page
#     scripts = soup.find_all("script")
#     entries = []
#     for script in scripts:
#         if "global.document.metadata" in script.text:
#             try:
#                 import json
#                 json_text = script.string.split("=",1)[1].strip().rstrip(";")
#                 metadata = json.loads(json_text)
#                 records = metadata.get("records", [])
#                 for rec in records[:max_results]:
#                     entries.append({
#                         "title": rec.get("articleTitle"),
#                         "summary": rec.get("abstract"),
#                         "authors": [a.get("name") for a in rec.get("authors", [])],
#                         "categories": rec.get("ieeeTerms", []),
#                         "pdf": rec.get("pdfLink"),
#                         "source": "IEEE"
#                     })
#                 break
#             except Exception as e:
#                 print("Failed to parse IEEE metadata:", e)
    
#     return {"entries": entries}


# # --------------------------
# # Combined Tool
# # --------------------------
# @tool
# def paper_search(topic: str, sources: list[str] = ["arxiv", "ieee"]) -> list[dict]:
#     """Search both arXiv and IEEE Xplore for papers."""
#     all_entries = []
#     if "arxiv" in sources:
#         print("Searching arXiv...")
#         arxiv_data = search_arxiv_papers(topic)
#         all_entries.extend(arxiv_data["entries"])
#     if "ieee" in sources:
#         print("Searching IEEE Xplore...")
#         ieee_data = search_ieee_papers(topic)
#         all_entries.extend(ieee_data["entries"])
    
#     if not all_entries:
#         raise ValueError(f"No papers found for topic: {topic} in sources: {sources}")
    
#     print(f"Found {len(all_entries)} papers for topic: {topic}")
#     return all_entries

import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from langgraph.graph import START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# ----------------------------
# Step 1: arXiv search
# ----------------------------
def search_arxiv_papers(topic: str, max_results: int = 5) -> list[dict]:
    query = "+".join(topic.lower().split())
    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query=all:{query}"
        f"&max_results={max_results}"
        "&sortBy=submittedDate"
        "&sortOrder=descending"
    )
    resp = requests.get(url)
    if not resp.ok:
        raise ValueError(f"Bad response from arXiv API: {resp.status_code}")
    
    # Parse XML
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(resp.text)
    entries = []
    for entry in root.findall("atom:entry", ns):
        authors = [author.findtext("atom:name", namespaces=ns) for author in entry.findall("atom:author", ns)]
        categories = [cat.attrib.get("term") for cat in entry.findall("atom:category", ns)]
        pdf_link = next((link.attrib.get("href") for link in entry.findall("atom:link", ns) if link.attrib.get("type") == "application/pdf"), None)
        entries.append({
            "title": entry.findtext("atom:title", namespaces=ns),
            "summary": entry.findtext("atom:summary", namespaces=ns).strip(),
            "authors": authors,
            "categories": categories,
            "pdf": pdf_link,
            "source": "arXiv"
        })
    return entries

# ----------------------------
# Step 2: IEEE search
# ----------------------------
def search_ieee_papers(topic: str, max_results: int = 5) -> list[dict]:
    url = "https://ieeexplore.ieee.org/rest/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://ieeexplore.ieee.org",
        "Referer": "https://ieeexplore.ieee.org/"
    }
    payload = {
        "queryText": topic,
        "highlight": True,
        "returnFacets": ["ALL"],
        "returnType": "SEARCH",
        "rowsPerPage": max_results,
        "pageNumber": 1
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if not resp.ok:
            print(f"IEEE API request failed: {resp.status_code} - {resp.text[:200]}")
            return []  # Return empty list instead of raising exception
        
        data = resp.json()
        entries = []
        for rec in data.get("records", [])[:max_results]:
            # Get the PDF link and construct a full URL if needed
            pdf_link = rec.get("pdfLink", "")
            if pdf_link:
                # If it's a relative path, construct full URL
                if not pdf_link.startswith("http"):
                    # Try to get the document ID for proper URL construction
                    doc_id = rec.get("articleNumber") or rec.get("documentLink", "").split("/")[-1]
                    if doc_id:
                        pdf_link = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                    else:
                        pdf_link = f"https://ieeexplore.ieee.org{pdf_link}" if pdf_link.startswith("/") else ""
            
            entries.append({
                "title": rec.get("articleTitle"),
                "summary": rec.get("abstract"),
                "authors": [a.get("name") for a in rec.get("authors", [])],
                "categories": rec.get("ieeeTerms", []),
                "pdf": pdf_link,
                "source": "IEEE"
            })
        return entries
    except Exception as e:
        print(f"IEEE search error: {str(e)}")
        return []  # Return empty list on any error

# ----------------------------
# Step 3: Unified tool
# ----------------------------
@tool
def paper_search(topic: str, sources: list[str] = ["arXiv", "IEEE"], max_results: int = 5) -> list[dict]:
    """
    Search academic papers across multiple sources (arXiv and IEEE).

    Args:
        topic: Topic to search for.
        sources: List of sources, e.g., ["arXiv", "IEEE"]
        max_results: Max papers per source.

    Returns:
        List of papers with metadata including title, authors, summary, pdf, source.
    """
    all_papers = []
    if "arXiv" in sources:
        print(f"Searching arXiv for: {topic}")
        all_papers.extend(search_arxiv_papers(topic, max_results))
    if "IEEE" in sources:
        print(f"Searching IEEE Xplore for: {topic}")
        all_papers.extend(search_ieee_papers(topic, max_results))
    
    if not all_papers:
        raise ValueError(f"No papers found for topic: {topic} in sources: {sources}")
    
    print(f"Found {len(all_papers)} papers for topic: {topic}")
    return all_papers
