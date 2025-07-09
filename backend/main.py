from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Translation Service Backend is running!"}
