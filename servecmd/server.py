from typing import Union
import json
from fastapi import FastAPI, Request, UploadFile
from . import util
from . import cmd_manager
from .cmd_session import process_web_cmd

app = FastAPI()


@app.post('/run/')
async def test_run(req: Request):
    processed = await util.process_request(req)
    cmd = processed['json'].pop('cmd', None)
    if not cmd:
        return {'code': 1, 'message': 'No cmd provided.'}
    ret = await process_web_cmd(cmd, processed['json'], processed['files'])
    return {'code': 0, 'message': 'ok', 'data': ret}


@app.get('/cmds/')
async def test_cmds():
    '''
    Return the list of available commands.
    '''
    cmd_names = cmd_manager.get_cmd_names()
    return {'code': 0, 'message': 'ok', 'data': cmd_names}


@app.get('/help/cmd/{cmd_name}/')
async def help_cmd(cmd_name: str):
    '''
    '''
    cmd_config = cmd_manager.get_cmd_config(cmd_name)
    data = {
        'name': cmd_name,
        'description': cmd_config.get('description', ''),
        'help': cmd_config.get('help', ''),
    }
    return {'code': 0, 'message': 'ok', 'data': data}
