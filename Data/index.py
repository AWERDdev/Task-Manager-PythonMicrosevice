from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from mongoengine import connect
from Routes.LinkedLists import router as linked_lists_router
from mongoengine import Document, StringField
from Routes.PreIndexedTagsSearch import router as Pre_Indexed_Tags_Search
import traceback
import logging
from config import DEBUG_MODE

# Initialize FastAPI app
app = FastAPI(debug=DEBUG_MODE)

# In your exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = {
        "error": str(exc),
    }
    
    # Only include traceback in debug mode
    if DEBUG_MODE:
        error_detail["traceback"] = traceback.format_exc()
        error_detail["type"] = type(exc).__name__
    
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": error_detail if DEBUG_MODE else None,
        }
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Connect to MongoDB using mongoengine
connect('TaskMaster', host='mongodb://127.0.0.1:27017/')

# Define a MongoEngine model for the Task (ensure consistency with your schema)
class Task(Document):
    userId = StringField(required=True)  # userId field (make sure it's the same in MongoDB)
    taskName = StringField()
    description = StringField()
    meta = {'collection': 'tasks'}  # Ensure it uses the 'tasks' collection

# Initialize FastAPI app with debug mode enabled
app = FastAPI(debug=True)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = {
        "error": str(exc),
        "type": type(exc).__name__,
        "traceback": traceback.format_exc()
    }
    logger.error(f"Unhandled exception: {error_detail}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": error_detail,
        }
    )

# Custom exception handler for HTTP exceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP exception: {exc.detail}, status_code: {exc.status_code}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": str(exc.detail),
            "status_code": exc.status_code
        }
    )

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    logger.error(f"Validation error: {error_details}")
    return JSONResponse(
        status_code=422,
        content={
            "message": "Validation error",
            "detail": error_details
        }
    )

# Middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise

# Register routers correctly
app.include_router(linked_lists_router, prefix="/api")
app.include_router(Pre_Indexed_Tags_Search, prefix="/api")

@app.get("/")
def home():
    return {"message": "Hello, FastAPI!"}

# Add a test endpoint to check error handling
@app.get("/test-error")
def test_error():
    # This will trigger our custom error handler
    raise ValueError("This is a test error to check error handling")
