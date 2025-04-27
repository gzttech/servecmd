import json
import logging
import datetime
import asyncio
import subprocess
from string import Template
from starlette.datastructures import UploadFile


logger = logging.getLogger('servecmd')

def json_log_info(data):
    data['created'] = datetime.datetime.now().isoformat()
    logger.info(json.dumps(data))


# back patch for string.Template.get_identifiers()
if not hasattr(Template, 'get_identifiers'):
    def get_identifiers(self):
        ids = []
        for mo in self.pattern.finditer(self.template):
            named = mo.group('named') or mo.group('braced')
            if named is not None and named not in ids:
                # add a named group only the first time it appears
                ids.append(named)
            elif (named is None
                and mo.group('invalid') is None
                and mo.group('escaped') is None):
                # If all the groups are None, there must be
                # another group we're not expecting
                raise ValueError('Unrecognized named group in pattern',
                    self.pattern)
        return ids
    Template.get_identifiers = get_identifiers


def update_model_instance(inst, **kwargs):
    for key, value in kwargs.items():
        setattr(inst, key, value)
    return inst


async def process_request(req):
    files = []
    json_data = {}
    content_type = (req.headers.get('content-type') or '').lower()
    if content_type == 'application/json':
        json_data = await req.json()
    elif content_type.startswith('multipart/form-data'):
        async with req.form() as form:
            for key in form:
                values = form.getlist(key)
                if not values:
                    continue
                if values[0].content_type == 'application/json':
                    json_data = json.loads(values[0].file.read())
                elif isinstance(values[0], UploadFile):
                        for value in values:
                            files.append({
                                'key': key,
                                'filename': value.filename,
                                'size': value.size,
                                'file': value.file.read()
                            })
    return {'json': json_data, 'files': files}


async def asyncio_call(cmd: str, **proc_kwargs):
    '''
    Use asyncio.create_subprocess_shell() to run a command,
    suitable for io-bound tasks.
    '''
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **proc_kwargs
     )
    (stdout, stderr) = await process.communicate()
    return (stdout, stderr, process)


async def subprocess_call(cmd: str, **proc_kwargs):
    '''
    Use subprocess.Popen() to run a command,
    suitable for cpu-bound tasks.
    '''
    def _run():
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **proc_kwargs
        )
        (stdout, stderr) = process.communicate()
        return (stdout, stderr, process)
    return await asyncio.to_thread(_run)
