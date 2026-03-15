import pdfplumber
import pytesseract
from PIL import Image
import io
import os
import shutil

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

def extract_text_from_pdf(file_contents):
    """Extracts text from a PDF file using pdfplumber."""
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(file_contents)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_contents):
    """Extracts text from a .docx file using python-docx."""
    if not HAS_DOCX:
        print("Warning: python-docx not installed. Skipping DOCX extraction.")
        return ""
    try:
        doc = docx.Document(io.BytesIO(file_contents))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text).strip()
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_image(file_contents):
    """Extracts text from an image using pytesseract."""
    if not shutil.which('tesseract'):
        return None # Special value to indicate binary missing
        
    try:
        image = Image.open(io.BytesIO(file_contents))
        # Note: This requires the tesseract binary to be installed on the system path
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        # Fallback graceful failure if tesseract is missing
        print(f"Error extracting text from Image: {e}")
        return ""

def extract_text_from_any(uploaded_file):
    """Routes the file to the correct extractor based on type."""
    if uploaded_file is None:
        return ""
        
    file_contents = uploaded_file.read()
    # Reset file pointer for later use (e.g. saving)
    uploaded_file.seek(0)
    
    file_name = uploaded_file.name.lower()
    extracted_text = ""
    
    if file_name.endswith('.pdf'):
        extracted_text = extract_text_from_pdf(file_contents)
    elif file_name.endswith('.docx'):
        extracted_text = extract_text_from_docx(file_contents)
    elif file_name.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp')):
        extracted_text = extract_text_from_image(file_contents)
    elif file_name.endswith(('.txt', '.md', '.log', '.csv')):
        try:
            extracted_text = file_contents.decode('utf-8', errors='ignore')
        except:
            extracted_text = ""
    elif file_name.endswith(('.xlsx', '.xls')):
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(file_contents))
            # Convert first few rows to string to get headers and some context
            extracted_text = "Excel Content Summary:\n" + df.head(20).to_string()
        except Exception as e:
            print(f"Error extracting text from Excel: {e}")
            extracted_text = ""
    
    # Smart Trimming for Large Logs/Files (Prevent LLM Context Overflow)
    # If text is > 8000 chars, take first 4000 and last 4000 to catch errors in logs
    if len(extracted_text) > 8000:
        first_part = extracted_text[:4000]
        last_part = extracted_text[-4000:]
        extracted_text = f"{first_part}\n\n[... TRUNCATED MIDDLE CONTENT ...]\n\n{last_part}"
        
    return extracted_text
