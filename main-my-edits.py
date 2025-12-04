from fastapi import FastAPI, UploadFile, File
from pa_validator.validators import (legal_clause_validator, 
    service_description_validator, template_validator)
import PyPDF2
from legal_redline_diff_engine import get_legal_redline_for_document, load_knowledge_base

app = FastAPI(title="Project Agreement Validator")
 
@app.post("/validate/")
async def validate_document(file: UploadFile = File(...)):
 
    # OCR to extract the document contents - ocr folder
    pdf_reader = PyPDF2.PdfReader(file.file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text() or ""
        text += page_text

    # Utility functions - utils folder
    ''' 
    1. Get template document - return template
    2. Tag different sections - return sections with tags
    '''

    # Validation logic - validators folder
    legal_status, legal_changes = legal_clause_validator.validate(text)
    service_status, service_changes = service_description_validator.validate(text)

    # Intermediate JSON structure for template validation
    template_details = template_validator(text)

    # Load knowledge base (uses default if you don't pass a path)
    knowledge_base = load_knowledge_base()

    # Pass extracted template sections into the redline engine
    legal_redline_result = get_legal_redline_for_document(
        document_text=text,
        extracted_sections=template_details,
        knowledge_base=knowledge_base,
    )

    # Final JSON response structure
    response = {
        "template_details": template_details,
        "legal_clauses": {
            "status": legal_status,
            "changes": legal_changes
        },
        "service_description": {
            "status": service_status,
            "changes": service_changes
        },
        "legal_redline_diff": legal_redline_result
    }
    return response
