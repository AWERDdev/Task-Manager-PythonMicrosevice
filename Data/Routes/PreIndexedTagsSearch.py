from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import jwt
from pymongo import MongoClient
from bson.objectid import ObjectId
from typing import List, Optional

# Secret key for JWT verification (must match the frontend's secret)
JWT_SECRET = "your_secret_key"
router = APIRouter()

# Connect to MongoDB using PyMongo
client = MongoClient('mongodb://127.0.0.1:27017/')
db = client['TaskMasterPublic']
# db = client['TaskMaster'] Private server
tasks_collection = db['tasks']

# Global variables for task storage and indexing
tasks_array = []
TasksIndex = defaultdict(list)  # Using defaultdict to avoid checking if key exists

# Define models for requests
class TokenRequest(BaseModel):
    token: str

class SearchRequest(BaseModel):
    token: str
    search_terms: List[str]

def verify_token(token: str):
    """Verify and decode JWT token."""
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def build_index(user_id: str):
    """Build or rebuild the search index for a specific user."""
    # Clear existing data for this user
    global tasks_array
    tasks_array = []
    TasksIndex.clear()
    
    # Fetch all tasks for the user
    tasks_cursor = tasks_collection.find({"userId": str(user_id)})
    
    # Process each task
    for task in tasks_cursor:
        task_id = str(task.get("_id"))
        task_title = task.get("TaskTitle", "Untitled")
        task_description = task.get("Task", "No description")
        
        # Store the task in our array
        task_data = {
            "id": task_id,
            "TaskTitle": task_title,
            "Task": task_description,
            "importance": task.get("importance", "Low"),
            "type": task.get("type", "General"),
            "Due": task.get("Due", "No due date")
        }
        tasks_array.append(task_data)
        
        # Index the task by words in title and description
        index_task(task_id, task_title, task_description)
    
    return tasks_array

def index_task(task_id: str, title: str, description: str):
    """Index a task by its title and description words."""
    # Process title
    if title:
        words = title.lower().split()
        for word in words:
            # Remove any punctuation
            word = word.strip('.,!?;:()[]{}"\'-')
            if word and len(word) > 2:  # Only index words longer than 2 characters
                TasksIndex[word].append(task_id)
    
    # Process description
    if description:
        words = description.lower().split()
        for word in words:
            # Remove any punctuation
            word = word.strip('.,!?;:()[]{}"\'-')
            if word and len(word) > 2:  # Only index words longer than 2 characters
                TasksIndex[word].append(task_id)

@router.post("/build-index")
async def build_search_index(request: TokenRequest):
    """Build or rebuild the search index for a user."""
    try:
        decoded_client_token = verify_token(request.token)
        user_id = decoded_client_token.get("id") or decoded_client_token.get("_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token does not contain user ID")
        
        tasks = build_index(user_id)
        
        return {
            "success": True, 
            "message": f"Index built successfully with {len(tasks)} tasks",
            "index_size": len(TasksIndex)
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_tasks(request: SearchRequest):
    """Search for tasks using the pre-built index."""
    try:
        decoded_client_token = verify_token(request.token)
        user_id = decoded_client_token.get("id") or decoded_client_token.get("_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token does not contain user ID")
        
        # If the index is empty, build it first
        if not TasksIndex:
            build_index(user_id)
        
        # Process search terms
        search_results = set()
        for term in request.search_terms:
            term = term.lower().strip()
            if term in TasksIndex:
                # Add all task IDs that match this term
                search_results.update(TasksIndex[term])
        
        # Get the full task details for the matching IDs
        matching_tasks = []
        for task in tasks_array:
            if task["id"] in search_results:
                matching_tasks.append(task)
        
        return {
            "success": True,
            "tasks": matching_tasks,
            "count": len(matching_tasks),
            "message": f"Found {len(matching_tasks)} tasks matching your search"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search-by-term")
async def search_by_term(token: str = Query(...), term: str = Query(...)):
    """Simple GET endpoint to search by a single term."""
    try:
        decoded_client_token = verify_token(token)
        user_id = decoded_client_token.get("id") or decoded_client_token.get("_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token does not contain user ID")
        
        # If the index is empty, build it first
        if not TasksIndex:
            build_index(user_id)
        
        # Process the search term
        term = term.lower().strip()
        matching_task_ids = TasksIndex.get(term, [])
        
        # Get the full task details for the matching IDs
        matching_tasks = []
        for task in tasks_array:
            if task["id"] in matching_task_ids:
                matching_tasks.append(task)
        
        return {
            "success": True,
            "tasks": matching_tasks,
            "count": len(matching_tasks),
            "message": f"Found {len(matching_tasks)} tasks matching '{term}'"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Function to update the index when a task is deleted
def update_index_after_delete(task_id, task_title=None, task_description=None):
    """Remove a task from the index when it's deleted."""
    try:
        # Remove the task ID from all index entries
        for term, task_ids in TasksIndex.items():
            if task_id in task_ids:
                TasksIndex[term].remove(task_id)
                # Clean up empty entries
                if not TasksIndex[term]:
                    del TasksIndex[term]
        
        # Also remove from tasks_array
        global tasks_array
        tasks_array = [task for task in tasks_array if task["id"] != task_id]
        
        print(f"Task {task_id} removed from index successfully")
        return True
    except Exception as e:
        print(f"Error updating index after delete: {e}")
        return False
