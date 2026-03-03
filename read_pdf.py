from langchain_core.tools import tool
import io
from pypdf import PdfReader
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
        # Validate source - must be a valid URL or local path
        if not source:
            raise ValueError("Source cannot be empty")
        
        # Check if it's a valid URL (must start with http:// or https://)
        if not (source.lower().startswith("http://") or source.lower().startswith("https://")):
            # If it's not a valid URL, check if it's a local file path
            if not Path(source).exists():
                raise ValueError(f"Invalid source: {source}. Must be a valid URL (http:// or https://) or an existing local file path.")
        
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
                    # IEEE stamp page contains PDF in an embed or via a specific URL pattern
                    # Try to find the PDF in an embed tag or iframe
                    embed_match = re.search(r'<embed[^>]+src="([^"]+\.pdf)"', response.text, re.IGNORECASE)
                    iframe_match = re.search(r'<iframe[^>]+src="([^"]+\.pdf)"', response.text, re.IGNORECASE)
                    
                    # Also try to find the direct PDF URL pattern
                    direct_pdf_match = re.search(r'(https://ieeexplore\.ieee\.org/document/\d+)', response.text)
                    
                    if embed_match:
                        actual_pdf_url = embed_match.group(1)
                        print(f"IEEE embed detected, downloading from: {actual_pdf_url}")
                        response = session.get(actual_pdf_url, headers=headers, timeout=30)
                    elif iframe_match:
                        actual_pdf_url = iframe_match.group(1)
                        print(f"IEEE iframe detected, downloading from: {actual_pdf_url}")
                        response = session.get(actual_pdf_url, headers=headers, timeout=30)
                    elif direct_pdf_match:
                        # Try to get PDF from the document page
                        doc_url = direct_pdf_match.group(1) + "/pdf"
                        print(f"IEEE document page detected, trying: {doc_url}")
                        response = session.get(doc_url, headers=headers, timeout=30)
                    else:
                        # Last resort: try adding /pdf to the stamp URL
                        pdf_url = source.replace("/stamp/stamp.jsp", "/stampPDF/download")
                        print(f"Trying IEEE PDF download URL: {pdf_url}")
                        response = session.get(pdf_url, headers=headers, timeout=30)
                
                pdf_file = io.BytesIO(response.content)
                print(f"Downloaded PDF from URL: {source}")
            elif "arxiv.org" in source:
                session = requests.Session()
                response = session.get(source, headers=headers, timeout=30, allow_redirects=True)
                if not response.content.startswith(b"%PDF"):
                    if "/abs/" in source:
                        pdf_url = source.replace("/abs/", "/pdf/") + ".pdf"
                    elif "/html/" in source:
                        pdf_url = source.replace("/html/", "/pdf/")
                    else:
                        pdf_url = source
                    print(f"arXiv redirect detected, trying: {pdf_url}")
                    response = session.get(pdf_url, headers=headers, timeout=30)
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
        pdf_reader = PdfReader(pdf_file)
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

    except ValueError:
        # Re-raise ValueError to preserve the original error message
        raise
    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        raise
