from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
openai_client = ""

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # or ["*"] for dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root_controller():
    return {"status": "healthy"}

@app.get("/chat-rep")
def chat_completion(prompt: str):
    response = prompt
    return {"statement": response}

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
