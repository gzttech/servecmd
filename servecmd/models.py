from typing import Literal, Union
from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    cmd_config_dirs: list[str] = Field(default_factory=list)
    default_workdir: str
    no_clean: bool | Literal['error'] = False
    verbosity: int = 0


class CmdConfig(BaseModel):
    name: str
    description: str = ''
    command: list[Union[str, dict]]
    cwd: str = ''
    params: dict = Field(default_factory=dict)
    runner: str | None = 'subprocess'
    lexer: str | None = 'shlex'
    return_: list = Field(default_factory=list, alias="return")