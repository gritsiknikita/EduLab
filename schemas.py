from pydantic import BaseModel

class RegisterIn(BaseModel):
    email: str
    password: str
    role: str = "teacher"

class LoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class WorkstationOut(BaseModel):
    id: int
    pc_id: str
    name: str
    room: str
    online: bool
    locked: bool

class CommandIn(BaseModel):
    type: str
    payload: dict = {}
