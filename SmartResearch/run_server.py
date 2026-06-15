import uvicorn
from src.main import app
print("App imported, starting server...", flush=True)
uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
