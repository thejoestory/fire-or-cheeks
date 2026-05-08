from pydantic import BaseModel, field_validator
from typing import Optional


class CreateGameRequest(BaseModel):
    title: str
    pin: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v[:80]


class JoinGameRequest(BaseModel):
    code: str
    display_name: str

    @field_validator("code")
    @classmethod
    def code_upper(cls, v):
        return v.strip().upper()

    @field_validator("display_name")
    @classmethod
    def name_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Display name cannot be empty")
        return v[:30]


class StartRoundRequest(BaseModel):
    prompt: Optional[str] = None
    pin: str


class VoteRequest(BaseModel):
    vote_value: str

    @field_validator("vote_value")
    @classmethod
    def valid_vote(cls, v):
        if v not in ("fire", "cheeks"):
            raise ValueError("Vote must be fire or cheeks")
        return v
