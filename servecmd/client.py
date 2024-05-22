import json
import mimetypes
import requests

TIMEOUT = 60 * 10


def api_call(url, cmd, json_data=None, files=None):
    json_data = json_data or {}
    json_data['cmd'] = cmd
    post_data = {}
    if isinstance(files, dict):
        for name, file in files.items():
            post_data[name] = (name, file, mimetypes.guess_type(name)[0])
    post_data['json'] = ('json', json.dumps(json_data), 'application/json')
    resp = requests.post(url, files=post_data, timeout=TIMEOUT)
    return resp