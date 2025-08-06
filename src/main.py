from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
# from utils.db import init_db
from src.utils.db import init_db, drop_db
from src.utils.redis import setup_redis
from src.v1.auth.routes import auth_router
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import Settings 
from src.utils.exception import register_error_handlers
from src.v1.route.twitter import twitter_router
@asynccontextmanager
async def life_span(app: FastAPI):
    """
    Lifecycle event handler for the FastAPI application.

    This asynchronous function is called when the FastAPI application starts up
    and shuts down. It initializes the database on startup and performs cleanup
    on shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: This function yields control back to the application after startup.
    """
    
    # print(f"dropping db....")
    # await drop_db()
    # print(f"db dropped")
    
    # Startup: Initialize the database
    print(f"server is starting....")
    await init_db()
    print(f"server has started!!")
    
    print(f"redis is starting....")
    await setup_redis()
    print(f"redis has started!!")
    yield  # Yield control back to FastAPI
    
    # Shutdown: Perform any necessary cleanup
    print(f"server is ending.....")

app = FastAPI(
    lifespan=life_span
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#register error handlers 
register_error_handlers(app)

#register routers/blueprint
app.include_router(auth_router)
app.include_router(twitter_router)


@app.get("/")
def root():
    """
    Root endpoint for the FastAPI application.

    Returns:
        str: A simple greeting message.
    """
    return {"message": "Hello World"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app",  port=8000, reload=True, host="0.0.0.0")
    



