"""
ABOUTME: Document parser for extracting content from PDF and Word files.
ABOUTME: Used to prepare documents for blog refresh functionality.
"""

import logging
import re
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_content: bytes) -> dict:
    """
    Extract text content from a PDF file using PyMuPDF.
    
    Args:
        file_content: Raw bytes of the PDF file
        
    Returns:
        dict with 'content' (extracted text), 'title' (if found), 'page_count'
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(stream=file_content, filetype="pdf")
        
        text_parts = []
        title = None
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            text_parts.append(page_text)
            
            # Try to extract title from first page (usually larger text)
            if page_num == 0 and not title:
                # Look for first non-empty line as potential title
                lines = [l.strip() for l in page_text.split('\n') if l.strip()]
                if lines:
                    title = lines[0][:200]  # Limit title length
        
        full_text = "\n\n".join(text_parts)
        
        # Clean up the text
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Remove excessive newlines
        full_text = full_text.strip()
        
        doc.close()
        
        return {
            "success": True,
            "content": full_text,
            "title": title,
            "page_count": len(text_parts),
            "word_count": len(full_text.split()),
        }
        
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        return {
            "success": False,
            "error": "PDF parsing library not available",
            "content": "",
        }
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": "",
        }


def extract_text_from_docx(file_content: bytes) -> dict:
    """
    Extract text content from a Word (.docx) file using python-docx.
    
    Args:
        file_content: Raw bytes of the DOCX file
        
    Returns:
        dict with 'content' (extracted text), 'title' (if found)
    """
    try:
        from docx import Document
        
        doc = Document(BytesIO(file_content))
        
        paragraphs = []
        title = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
                
                # First heading or paragraph could be the title
                if not title and para.style.name.startswith('Heading'):
                    title = text[:200]
                elif not title and len(paragraphs) == 1:
                    title = text[:200]
        
        full_text = "\n\n".join(paragraphs)
        
        return {
            "success": True,
            "content": full_text,
            "title": title,
            "paragraph_count": len(paragraphs),
            "word_count": len(full_text.split()),
        }
        
    except ImportError:
        logger.error("python-docx not installed. Run: pip install python-docx")
        return {
            "success": False,
            "error": "Word parsing library not available",
            "content": "",
        }
    except Exception as e:
        logger.error(f"Failed to parse DOCX: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": "",
        }


def extract_keyword_from_content(content: str, title: Optional[str] = None) -> str:
    """
    Attempt to extract a keyword/topic from the document content.
    
    Uses the title if available, otherwise extracts from first paragraph.
    """
    if title:
        # Clean up title to use as keyword
        keyword = title.strip()
        # Remove common prefixes
        for prefix in ['How to', 'What is', 'Guide to', 'The Ultimate', 'A Complete']:
            if keyword.lower().startswith(prefix.lower()):
                keyword = keyword[len(prefix):].strip()
        return keyword[:100]  # Limit length
    
    if content:
        # Use first sentence or first 100 chars
        first_line = content.split('\n')[0].strip()
        if len(first_line) > 100:
            first_line = first_line[:100] + "..."
        return first_line
    
    return "document content"


def parse_document(file_content: bytes, filename: str) -> dict:
    """
    Parse a document (PDF or DOCX) and extract content for blog refresh.
    
    Args:
        file_content: Raw bytes of the file
        filename: Original filename (used to determine type)
        
    Returns:
        dict with 'content', 'keyword', 'title', and metadata
    """
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        result = extract_text_from_pdf(file_content)
    elif filename_lower.endswith('.docx'):
        result = extract_text_from_docx(file_content)
    elif filename_lower.endswith('.doc'):
        # .doc files are not supported by python-docx
        return {
            "success": False,
            "error": "Legacy .doc format not supported. Please convert to .docx",
            "content": "",
        }
    else:
        return {
            "success": False,
            "error": f"Unsupported file type: {filename}",
            "content": "",
        }
    
    if result.get("success"):
        # Add keyword extraction
        result["keyword"] = extract_keyword_from_content(
            result.get("content", ""),
            result.get("title")
        )
        result["filename"] = filename
    
    return result
