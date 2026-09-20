from fastapi import APIRouter, HTTPException
from app.services import dynamodb as db

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{user_id}")
def list_evidence(user_id: str):
    items = db.get_evidence(user_id)
    return {"user_id": user_id, "evidence": items, "count": len(items)}


@router.get("/{user_id}/{evidence_id}")
def get_evidence(user_id: str, evidence_id: str):
    item = db.get_item(f"USER#{user_id}", f"EVIDENCE#{evidence_id}")
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return item
