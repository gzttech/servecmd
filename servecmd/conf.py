import json
import os
import logging
import yaml
from .util import update_model_instance
from .models import GlobalConfig

CONFIG = GlobalConfig(
    default_workdir=f'{os.getcwd()}/servecmd_default'
)

CONFIG_SEARCH_LOCATIONS = [
    'servecmd.yaml',
    'servecmd.json',
]


def setup_logging():
    logger = logging.getLogger('servecmd')
    logger.addHandler(logging.StreamHandler())
    if CONFIG.verbosity == 1:
        logger.setLevel(logging.INFO)
    if CONFIG.verbosity > 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


import os

def load(config_file=None):
    locations = []
    if config_file:
        locations.append(config_file)
    else:
        locations.extend(CONFIG_SEARCH_LOCATIONS)
    for location in locations:
        try:
            if os.path.isfile(location):
                with open(location) as f:
                    if location.endswith('.json'):
                        update_model_instance(CONFIG, **json.load(f))
                    elif location.endswith('.yaml') or location.endswith('.yml'):
                        update_model_instance(CONFIG, **yaml.safe_load(f))
                    else:
                        raise ValueError('Unsupported config file type')
            elif os.path.isdir(location):
                for root, _, files in os.walk(location):
                    for filename in files:
                        if filename.endswith('.json') or filename.endswith('.yaml') or filename.endswith('.yml'):
                            config_file = os.path.join(root, filename)
                            with open(config_file) as f:
                                update_model_instance(CONFIG, **yaml.safe_load(f))
        except FileNotFoundError:
            pass
    setup_logging()
