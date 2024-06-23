from fastapi import FastAPI

app = FastAPI()

@app.get("/wa")
@app.get("/test")

def welcome():
    return {
        "mymessage": "the thing are displyed via your team "


    }

