from . import conf
from . import cmd_session

CMD_CONFIG_STORE = {}


def load_cmd_configs():
    '''
    Load all the command configurations.
    '''
    for config_dir in conf.CONFIG.cmd_config_dirs:
        CMD_CONFIG_STORE.update(cmd_session.load_all_configs(config_dir))


def get_cmd_names():
    '''
    Get all the command names.
    '''
    return list(CMD_CONFIG_STORE.keys())


def get_cmd_config(name):
    '''
    Load the configuration from the config file.
    '''
    return CMD_CONFIG_STORE.get(name, {})