from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from document_extractor import DocumentExtractor
from contract_analyzer import ContractAnalyzer
from azure_clients import AzureClientManager
from servicenow_client import ServiceNowClient

app = FastAPI()

# Initialize ServiceNow client immediately since it's lightweight
service_now_client = ServiceNowClient()

# Lazy initialization for Azure clients
doc_extractor = None
contract_analyzer = None

def get_doc_extractor():
    global doc_extractor
    if doc_extractor is None:
        azure_client_manager = AzureClientManager()
        doc_extractor = DocumentExtractor(azure_client_manager.doc_client)
    return doc_extractor

def get_contract_analyzer():
    global contract_analyzer
    if contract_analyzer is None:
        azure_client_manager = AzureClientManager()
        contract_analyzer = ContractAnalyzer(azure_client_manager.openai_client)
    return contract_analyzer

@app.post("/contract/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        doc_extractor = get_doc_extractor()
        markdown_text, page_count, extraction_time = doc_extractor.extract_text(pdf_bytes)
        
        contract_analyzer = get_contract_analyzer()
        result_json, analysis_time, usage_stats = contract_analyzer.analyze(markdown_text)
        
        return {
            "extracted_sections": markdown_text,
            "page_count": page_count,
            "extraction_time_seconds": extraction_time,
            "analysis_result": result_json,
            "analysis_time_seconds": analysis_time,
            "usage_stats": usage_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/servicenow/{requestid}")
async def get_servicenow_metadata(requestid: str):
    try:
        raw, cleaned = service_now_client.get_record(requestid)
        if cleaned is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"metadata": cleaned, "sys_id": cleaned["sys_id"]}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/servicenow/{sys_id}/document")
async def download_servicenow_document(sys_id: str):
    try:
        attachment = service_now_client.download_attachment_bytes(sys_id)
        if attachment is None:
            raise HTTPException(status_code=404, detail="Attachment not found")
        return StreamingResponse(
            iter([attachment["bytes"]]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={attachment['file_name']}"}
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
