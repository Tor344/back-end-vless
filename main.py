import os

from dotenv import load_dotenv

from fastapi import FastAPI, Header, HTTPException, Security, Depends, Path, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import manager


load_dotenv()


security = HTTPBearer()


API_TOKEN = os.getenv("API_TOKEN")


app = FastAPI()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.scheme != "Bearer" or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing token")
    return True


@app.get("/")
async def root():
    return {"message": f"Hello"}


@app.get("/show_user")
async def show_user(auth: bool = Depends(verify_token)):
    count_users = manager.user_list()
    return {"count_user": count_users}


@app.post("/new_user/{name_user}")
async def new_user(name_user: str =  Path(..., min_length=1, max_length=10), auth: bool = Depends(verify_token)):
    text_config = manager.make_link_for_email(name_user)
    return {"link": text_config}


@app.delete("/delete_user/{name_user}")
async def delete_user(name_user: str =  Path(..., min_length=1, max_length=10), auth: bool = Depends(verify_token)):
    manager.remove_user_for_email(name_user)
    return {"message": f"User {name_user} deleted"}