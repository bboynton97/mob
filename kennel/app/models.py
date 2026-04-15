from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

GithubUser = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=39,
        pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$",
    ),
]
MachineFp = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
Pet = Annotated[
    str,
    StringConstraints(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$"),
]
DisplayName = Annotated[str, StringConstraints(min_length=1, max_length=40)]
PetName = Annotated[str, StringConstraints(min_length=1, max_length=40)]


class SubmitRequest(BaseModel):
    github_user: GithubUser
    machine_fp: MachineFp
    pet: Pet
    pet_name: PetName | None = None
    display_name: DisplayName
    xp: int = Field(ge=0)


class SubmitResponse(BaseModel):
    total_xp: int
    others_xp: int
    rank: int | None


class LeaderboardRow(BaseModel):
    rank: int
    github_user: str
    display_name: str
    pet: str
    xp: int


class LeaderboardResponse(BaseModel):
    top: list[LeaderboardRow]
    me: LeaderboardRow | None
