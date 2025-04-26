from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt
from pymongo import MongoClient
from bson.objectid import ObjectId
from .TaskIndexManager import update_index_after_delete


# Secret key for JWT verification (must match the frontend's secret)
JWT_SECRET = "your_secret_key"

router = APIRouter()

# Connect to MongoDB using PyMongo
client = MongoClient('mongodb://127.0.0.1:27017/')
db = client['TaskMasterPublic']
# db = client['TaskMaster'] Private server
tasks_collection = db['tasks']

# Define a model for the request body
class TokenRequest(BaseModel):
    token: str

def verify_token(token: str):
    """Verify and decode JWT token."""
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

class TaskNode:
    def __init__(self, task_id, task_title, task_description, importance, task_type, due_date):
        self.task_id = task_id
        self.task_title = task_title
        self.task_description = task_description
        self.importance = importance
        self.task_type = task_type
        self.due_date = due_date
        self.next = None  # Points to the next task node

class TaskLinkedList:
    def __init__(self):
        self.head = None

    def add_task(self, task_id, task_title, task_description, importance, task_type, due_date):
        new_node = TaskNode(task_id, task_title, task_description, importance, task_type, due_date)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node
    
    def remove_task(self, task_id):
        if not self.head:
            return False
            
        if self.head.task_id == task_id:
            self.head = self.head.next
            return True
            
        current = self.head
        while current.next and current.next.task_id != task_id:
            current = current.next
            
        if current.next:
            current.next = current.next.next
            return True
            
        return False
    
    def get_all_tasks(self):
        tasks = []
        current = self.head
        while current:
            tasks.append({
                "id": current.task_id,
                "TaskTitle": current.task_title,
                "Task": current.task_description,
                "importance": current.importance,
                "type": current.task_type,
                "Due": current.due_date
            })
            current = current.next
        return tasks

@router.post("/users")
async def get_users_tasks(user: TokenRequest):
    try:
        decoded_client_token = verify_token(user.token)
        user_id = decoded_client_token.get("id") or decoded_client_token.get("_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="Token does not contain user ID")

        task_linked_list = TaskLinkedList()
        tasks_cursor = tasks_collection.find({"userId": str(user_id)})
        # print(tasks_cursor)
        for task in tasks_cursor:
            task_linked_list.add_task(
                task_id=str(task.get("_id")),
                task_title=task.get("TaskTitle", "Untitled"),
                task_description=task.get("Task", "No description"),
                importance=task.get("importance", "Low"),
                task_type=task.get("type", "General"),
                due_date=task.get("Due", "No due date")
            )

        task_list = task_linked_list.get_all_tasks()

        if not task_list:
            return {"success": False, "message": "No tasks found for this user"}

        return {"success": True, "tasks": task_list, "message": "Tasks found successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
class DeleteTaskRequest(BaseModel):
    token: str
    task_id: str

@router.delete("/tasks")
async def delete_task(request: DeleteTaskRequest):
    try:
        decoded_client_token = verify_token(request.token)
        user_id = decoded_client_token.get("id") or decoded_client_token.get("_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token does not contain user ID")
        
        # Ensure task_id is a valid ObjectId
        try:
            task_object_id = ObjectId(request.task_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid task ID format")
        
        # Find the task first
        task = tasks_collection.find_one({"_id": task_object_id, "userId": str(user_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found or not authorized to delete")
        
        # Delete the task from the database
        result = tasks_collection.delete_one({"_id": task_object_id})
        
        if result.deleted_count == 1:
            # Update the TasksIndex after deletion
            task_id = str(task["_id"])
            update_index_after_delete(task_id)
            return {"success": True, "message": "Task deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete task")
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in delete_task: {str(e)}")  # Log the error
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
