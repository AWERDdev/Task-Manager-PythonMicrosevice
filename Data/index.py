from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from mongoengine import connect, Document, StringField
from Routes.LinkedLists import router as linked_lists_router
from Routes.PreIndexedTagsSearch import router as Pre_Indexed_Tags_Search
from config import DEBUG_MODE
import traceback
import logging

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(debug=DEBUG_MODE)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connections
connect('TaskMasterPublic', host='mongodb://127.0.0.1:27017/')
# connect('TaskMaster', host='mongodb://127.0.0.1:27017/')

# MongoEngine Task model
class Task(Document):
    userId = StringField(required=True)
    taskName = StringField()
    description = StringField()
    meta = {'collection': 'tasks'}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = {
        "error": str(exc),
    }
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

# HTTP exception handler
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

# Validation error handler
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

# Request logging middleware
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

# Register routers
app.include_router(linked_lists_router, prefix="/api")
app.include_router(Pre_Indexed_Tags_Search, prefix="/api")

# Home route
@app.get("/")
def home():
    return {"message": "Hello, FastAPI!"}

# Test error route
@app.get("/test-error")
def test_error():
    raise ValueError("This is a test error to check error handling")
