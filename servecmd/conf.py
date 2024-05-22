import json
import logging
import yaml

CONFIG = {

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
    logging.basicConfig(level=CONFIG.get('log_level', 'INFO'))