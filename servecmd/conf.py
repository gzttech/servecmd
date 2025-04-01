import json
import os
import logging
import yaml

CONFIG = {
    'default_workdir': f'{os.getcwd()}/servecmd_default',
    'no_clean': False,
    'verbosity': 0,
}

CONFIG_SEARCH_LOCATIONS = [
    'servecmd.yaml',
    'servecmd.json',
]


def load(config_file=None):
    locations = []
    if config_file:
        locations.append(config_file)
    else:
        locations.extend(CONFIG_SEARCH_LOCATIONS)
    for location in locations:
        try:
            with open(location) as f:
                if location.endswith('.json'):
                    CONFIG.update(json.load(f))
                elif location.endswith('.yaml') or location.endswith('.yml'):
                    CONFIG.update(yaml.safe_load(f))
                else:
                    raise ValueError('Unsupported config file type')
        except FileNotFoundError:
            pass
    # setup logging
    logger = logging.getLogger('servecmd')
    if CONFIG['verbosity'] == 1:
        logger.setLevel(logging.INFO)
    if CONFIG['verbosity'] > 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
