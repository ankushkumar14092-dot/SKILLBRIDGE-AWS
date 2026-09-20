from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.tools import extract_text_from_pdf, analyze_resume as parse_resume
from app.services import s3 as s3_service

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload")
async def upload_resume(user_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()

    try:
        s3_key = s3_service.upload_resume(user_id, pdf_bytes, file.filename)
    except Exception:
        s3_key = None  # S3 optional for local testing

    resume_text = extract_text_from_pdf(pdf_bytes)
    resume_data = parse_resume(resume_text)

    return {
        "user_id": user_id,
        "s3_key": s3_key,
        "resume_text": resume_text[:500] + "..." if len(resume_text) > 500 else resume_text,
        "resume_data": resume_data,
    }


@router.post("/analyze")
async def analyze_resume_text(payload: dict):
    """Analyze raw resume text without file upload."""
    resume_text = payload.get("resume_text", "")
    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text is required")
    return {"resume_data": parse_resume(resume_text)}
