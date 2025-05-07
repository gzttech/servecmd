import asyncio
import contextlib
import base64
import json
import os
import glob
import shlex
import shutil
import uuid
import time
import yaml
from . import conf
from . import cmd_manager
from . import util
from .models import CmdConfig


def load_cmd_config_from_file(filename, type=None):
    if type is None:
        type = filename.split('.')[-1]
    with open(filename) as fd:
        if type == 'json':
            return json.load(fd)
        elif type == 'yaml' or type == 'yml':
            return yaml.safe_load(fd)
        else:
            raise ValueError(f'Unsupported config file type: {type}')


def load_all_configs(directory):
    configs = {}
    for filename in os.listdir(directory):
        if filename.endswith('.json') or filename.endswith('.yaml') or filename.endswith('.yml'):
            config = CmdConfig(
                **load_cmd_config_from_file(f'{directory.rstrip("/")}/{filename}')
            )
            configs[config.name] = config
    return configs


def to_base64(data):
    data = data.read() if hasattr(data, 'read') else data
    return base64.b64encode(data).decode('utf-8')


class CmdSession:
    '''
    A cmd executing session.
    '''
    def __init__(self, cmd_config: CmdConfig):
        self.cmd_config = cmd_config
        self.job_id = None
        self._params_cache = {}

    @contextlib.asynccontextmanager
    async def job_context(self):
        job_context_dict = {
            'returncode': None,
            'has_exception': False,
        }
        self.job_id = str(uuid.uuid4())
        try:
            self.ensure_job_path()
            yield job_context_dict
        except Exception as e:
            job_context_dict['has_exception'] = True
            raise e
        finally:
            error_return_code = True if job_context_dict['returncode'] else False
            is_abnormal = error_return_code or job_context_dict['has_exception']
            match (is_abnormal, conf.CONFIG.no_clean):
                case (__, False):
                    self.clean_job_path()
                case (__, True):
                    pass
                case (True, 'error'):
                    pass
                case _:
                    self.clean_job_path()
            self.job_id = None

    def get_job_path(self):
        cwd = self.cmd_config.cwd or conf.CONFIG.default_workdir
        return f'{cwd.rstrip("/")}/{self.job_id}'
    
    def get_job_file_path(self, filename):
        return f'{self.get_job_path()}/{filename}'
    
    def ensure_job_path(self):
        job_path = self.get_job_path()
        os.makedirs(job_path, exist_ok=True)

    def clean_job_path(self):
        job_path = self.get_job_path()
        shutil.rmtree(job_path, ignore_errors=True)

    def get_params(self, *param_name_list, **kwargs):
        ret = {}
        params = self.cmd_config.params or {}
        for param_name in param_name_list:
            if param_name in self._params_cache:
                ret[param_name] = self._params_cache[param_name]
                continue
            param_config = params.get(param_name)
            if param_config is None:
                # if the param provided in the kwargs, retrieve it.
                if param_name in kwargs:
                    ret[param_name] = kwargs.get(param_name)
                # if the param is not defined in the config, skip it.
                else:
                    continue
            else:
                value = kwargs.get(param_name)
                if param_config.get('required') and value is None:
                    raise ValueError(f"Missing required param: {param_name}")
                if param_config.get('type') == 'file':
                    filename = param_config.get('filename') or param_name
                    ret[param_name] = filename
                elif param_config.get('type') == 'list':
                    param_list = ' '.join(value or [])
                    ret[param_name] = param_list
                else:
                    ret[param_name] = value
            self._params_cache[param_name] = ret[param_name]
        return ret
    
    async def preprocess_params(self, **kwargs):
        for param_name in (self.cmd_config.params or {}):
            __ = self.get_params(param_name, **kwargs)

    async def preprocess_files(self, files):
        for file in files:
            filename = file['filename'] or file['key']
            with open(self.get_job_file_path(filename), 'wb') as fd:
                content = file.get('file')
                if isinstance(content, str):
                    content = content.encode('utf-8')
                fd.write(content)

    def process_input_item(self, item, cmd_env, **kwargs):
        if item is None:
            return ''
        else:
            item = str(item)
        tmpl  = util.Template(item)
        param_name_list = tmpl.get_identifiers()
        if param_name_list:
            param_values = self.get_params(*param_name_list, **kwargs)
            return tmpl.safe_substitute(cmd_env, **param_values)
        else:
            return item

    async def prepare_cmd(self, *args, **kwargs):
        args_list = []
        cmd_env = {}
        cmd_env['cwd'] = self.get_job_path()
        cmd_env['cwd_abs'] = os.path.abspath(self.get_job_path())
        for item in self.cmd_config.command:
            processed_item = self.process_input_item(item, cmd_env, **kwargs)
            args_list.append(processed_item)
        if self.cmd_config.lexer:
            result_args_list = []
            for i in args_list:
                result_args_list.extend(shlex.split(i))
            return shlex.join(result_args_list)
        else:
            return ' '.join(args_list)

    async def execute(self, cmd, job_context_dict, **kwargs):
        ret = {}
        proc_kwargs = {}
        proc_kwargs['cwd'] = self.get_job_path()
        begin_time = time.time()
        if self.cmd_config.runner == 'subprocess':
            (stdout, stderr, process) = await util.subprocess_call(cmd, **proc_kwargs)
        else:
            (stdout, stderr, process) = await util.asyncio_call(cmd, **proc_kwargs)
        end_time = time.time()
        job_context_dict['returncode'] = process.returncode
        job_context_dict['stdout'] = stdout.decode('utf-8', 'ignore')
        job_context_dict['stderr'] = stderr.decode('utf-8', 'ignore')
        util.json_log_info({
            'job_id': self.job_id,
            'returncode': process.returncode,
            'used_time': end_time - begin_time,
            'stderr': stderr.decode('utf-8'),
        })
        for item in self.cmd_config.return_:
            if item == 'stdout':
                ret['stdout'] = stdout.decode('utf-8')
            elif item == 'stderr':
                ret['stderr'] = stderr.decode('utf-8')
            elif item == 'returncode':
                ret['returncode'] = process.returncode
            elif isinstance(item, dict):
                arg_name = item['name']
                arg_type = item['type']
                if arg_type == 'file':
                    with open(self.get_job_file_path(item['filename']), 'rb') as fd:
                        ret[arg_name] = {
                            'body': to_base64(fd),
                            'mimetype': item.get('mimetype', ''),
                            'encoding': item.get('encoding', 'base64')
                        }
                if arg_type in ['stdout', 'stderr']:
                    ret[arg_name] = {
                        'body': to_base64(stdout if arg_type == 'stdout' else stderr),
                        'mimetype': item.get('mimetype', ''),
                        'encoding': item.get('encoding', 'base64')
                    }
                elif arg_type == 'file_list':
                    ret[arg_name] = []
                    root_dir = self.get_job_path()
                    matched_filenames = []
                    if item.get('glob'):
                        matched_filenames = glob.glob(item['glob'], root_dir=root_dir)
                    for filename in matched_filenames:
                        with open(self.get_job_file_path(filename), 'rb') as fd:
                            ret[arg_name].append({
                                'body': to_base64(fd),
                                'fielname': filename,
                                'mimetype': item.get('mimetype', ''),
                                'encoding': item.get('encoding', 'base64')
                            })
        ret['job_id'] = self.job_id
        return ret

    async def run(self, files, **kwargs):
        async with self.job_context() as job_context_dict:
            await self.preprocess_files(files)
            await self.preprocess_params(**kwargs)
            cmd = await self.prepare_cmd(**kwargs)
            util.json_log_info({
                'job_id': self.job_id,
                'cmd': cmd})
            result = await self.execute(cmd, job_context_dict, **kwargs)
            if job_context_dict['returncode'] != 0:
                util.logger.info(job_context_dict['stdout'])
            else:
                util.logger.debug(job_context_dict['stdout'])
        return True, result


async def process_web_cmd(cmd, json_data, files):
    cmd_args = {}
    cmd_args.update(json_data)
    for file in files:
        cmd_args[file['filename']] = file['file']
    cmd_config = cmd_manager.get_cmd_config(cmd)
    if not cmd_config:
        return False, {'code': 1, 'message': f'Command {cmd} not found.'}
    cmd_session = CmdSession(cmd_config)
    return await cmd_session.run(files, **cmd_args)
