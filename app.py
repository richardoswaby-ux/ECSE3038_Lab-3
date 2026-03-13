from fastapi import FastAPI, HTTPException, status, Response
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID, uuid4
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values

#                Environment & Database setup 

config = dotenv_values(".env")
MONGO_URI = config["MONGO_URI"]

app = FastAPI()

# Initialize the Motor client using MONGO_URI
client = AsyncIOMotorClient(MONGO_URI)

db = client["engineering_db"]  

# Pydantic Models

class WorkOrder(BaseModel):
    # System-generated fields
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Client-provided fields
    title: str
    description: str
    assigned_to: str
    priority: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "in_progress", "completed", "cancelled"]

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    status: Optional[Literal["open", "in_progress", "completed", "cancelled"]] = None


#      REST API Endppoints

@app.post("/work-orders", status_code=status.HTTP_201_CREATED)
async def create_work_order(work_order: WorkOrder):
    
    doc = work_order.model_dump()
    doc["id"] = str(doc["id"])
    doc["created_at"] = doc["created_at"].isoformat()
    await db["work_orders"].insert_one(doc)
    
    return work_order
    

@app.get("/work-orders", status_code=status.HTTP_200_OK)
async def get_all_work_orders(priority: Optional[str] = None):
    query = {}
    if priority:
        query = {"priority": priority}
    
    work_orders = []
    
    async for doc in db["work_orders"].find(query, {"_id": 0}):
        work_orders.append(doc)
    return work_orders

@app.get("/work-orders/{work_order_id}", status_code=status.HTTP_200_OK)
async def get_work_order(work_order_id: str):
    doc = await db["work_orders"].find_one({"id": work_order_id}, {"_id": 0})
    
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
        
    return doc
    

@app.put("/work-orders/{work_order_id}", status_code=status.HTTP_200_OK)
async def replace_work_order(work_order_id: str, work_order: WorkOrder):
    update_data = work_order.model_dump(exclude={"id", "created_at"})
    result = await db["work_orders"].update_one({"id": work_order_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    doc = await db["work_orders"].find_one({"id": work_order_id}, {"_id": 0})
    return doc
    

@app.patch("/work-orders/{work_order_id}", status_code=status.HTTP_200_OK)
async def partial_update_work_order(work_order_id: str, work_order_update: WorkOrderUpdate):
    update_data = work_order_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided in patch")
        
    result = await db["work_orders"].update_one({"id": work_order_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
        
    doc = await db["work_orders"].find_one({"id": work_order_id}, {"_id": 0})
    return doc


@app.delete("/work-orders/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_order(work_order_id: str):
    result = await db["work_orders"].delete_one({"id": work_order_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")