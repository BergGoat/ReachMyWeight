from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welkom bij de rekenmachine-API!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/calculate")
def calculate(operation: str, x: float, y: float):
    if operation == "add":
        return {"result": x + y}
    elif operation == "subtract":
        return {"result": x - y}
    elif operation == "multiply":
        return {"result": x * y}
    elif operation == "divide":
        # Let op: niet op nul delen
        if y == 0:
            raise HTTPException(status_code=400, detail="Je kunt niet door nul delen.")
        return {"result": x / y}
    else:
        raise HTTPException(status_code=400, detail=f"Onbekende bewerking: {operation}")
