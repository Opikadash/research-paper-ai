from langchain_core.tools import tool
import io
import PyPDF2
import requests
from pathlib import Path
import re

@tool
def read_pdf(source: str) -> str:
    """Read and extract text from a PDF file given a URL or local path.

    Args:
        source: URL of the PDF or local file path

    Returns:
        The extracted text content from the PDF
    """
    try:
        # Determine if source is a URL
        if source.lower().startswith("http://") or source.lower().startswith("https://"):
            # For IEEE URLs, we need to handle the redirect properly
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/pdf,text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            # First check if it's an IEEE URL that needs special handling
            if "ieeexplore.ieee.org" in source:
                # Try with session to handle IEEE redirects
                session = requests.Session()
                response = session.get(source, headers=headers, timeout=30, allow_redirects=True)
                
                # Check if we got HTML instead of PDF (IEEE stamp page)
                content_type = response.headers.get("Content-Type", "")
                if "html" in content_type or not response.content.startswith(b"%PDF"):
                    # Try to find the actual PDF link in the HTML
                    pdf_match = re.search(r'(https://ieeexplore\.ieee\.org/stamp/stamp\.jsp\?tp=&arnumber=\d+)', response.text)
                    if pdf_match:
                        actual_pdf_url = pdf_match.group(1)
                        print(f"IEEE redirect detected, following to: {actual_pdf_url}")
                        response = session.get(actual_pdf_url, headers=headers, timeout=30)
                
                pdf_file = io.BytesIO(response.content)
                print(f"Downloaded PDF from URL: {source}")
            else:
                response = requests.get(source, headers=headers, timeout=30)
                pdf_file = io.BytesIO(response.content)
                print(f"Downloaded PDF from URL: {source}")
        else:
            # Treat as local file path
            pdf_file = open(Path(source), "rb")
            print(f"Reading PDF from local path: {source}")

        # Check if it's actually a PDF
        if pdf_file.read(4) != b"%PDF":
            pdf_file.seek(0)
            content = pdf_file.read(200).decode("utf-8", errors="ignore")
            raise ValueError(f"URL does not point to a valid PDF. Content type: {content[:100]}")
        
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        text = ""
        for i, page in enumerate(pdf_reader.pages, 1):
            print(f"Extracting text from page {i}/{num_pages}")
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        # Close file if local
        if not isinstance(pdf_file, io.BytesIO):
            pdf_file.close()

        if not text:
            raise ValueError("No text could be extracted from the PDF")
            
        print(f"Successfully extracted {len(text)} characters from PDF")
        return text.strip()

    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        raise
