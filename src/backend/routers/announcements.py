"""
Announcement management endpoints for Mergington High School API
"""

from fastapi import APIRouter, Depends, HTTPException
from src.backend.database import announcements_collection
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from src.backend.routers.auth import get_current_user
from bson import ObjectId

router = APIRouter()

class Announcement(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    title: str
    message: str
    created_at: datetime
    start_date: Optional[datetime] = None
    expiration_date: datetime
    author: str

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    start_date: Optional[datetime] = None
    expiration_date: datetime

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    start_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

# List all announcements (optionally filter expired)
@router.get("/announcements", response_model=List[Announcement])
def list_announcements(active_only: bool = True):
    now = datetime.utcnow()
    query = {"expiration_date": {"$gt": now}}
    if active_only:
        docs = announcements_collection.find(query)
    else:
        docs = announcements_collection.find({})
    result = []
    for doc in docs:
        if isinstance(doc.get("_id"), ObjectId):
            doc["_id"] = str(doc["_id"])
        result.append(Announcement(**doc))
    return result

# Add a new announcement (signed-in users only)
@router.post("/announcements", response_model=Announcement)
def add_announcement(data: AnnouncementCreate, user=Depends(get_current_user)):
    doc = {
        "title": data.title,
        "message": data.message,
        "created_at": datetime.utcnow(),
        "start_date": data.start_date,
        "expiration_date": data.expiration_date,
        "author": user["username"],
    }
    result = announcements_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return Announcement(**doc)

# Update an announcement (signed-in users only)
@router.put("/announcements/{announcement_id}", response_model=Announcement)
def update_announcement(announcement_id: str, data: AnnouncementUpdate, user=Depends(get_current_user)):
    update_fields = {k: v for k, v in data.dict(exclude_unset=True).items()}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update.")
    # Try both string and ObjectId for _id
    query = {"_id": ObjectId(announcement_id) if ObjectId.is_valid(announcement_id) else announcement_id}
    result = announcements_collection.find_one_and_update(
        query,
        {"$set": update_fields},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Announcement not found.")
    if isinstance(result.get("_id"), ObjectId):
        result["_id"] = str(result["_id"])
    return Announcement(**result)

# Delete an announcement (signed-in users only)
@router.delete("/announcements/{announcement_id}")
def delete_announcement(announcement_id: str, user=Depends(get_current_user)):
    query = {"_id": ObjectId(announcement_id) if ObjectId.is_valid(announcement_id) else announcement_id}
    result = announcements_collection.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found.")
    return {"success": True}
