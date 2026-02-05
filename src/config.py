import loggerric as lr
import os, json

class ConfigParser:
    """**Load and validate camera config from JSON**"""

    def __init__(self, path:str):
        lr.Log.debug(f'Initializing ConfigParser: {path}')

        self.path = path
        self.config = []
        
        if not os.path.exists(path):
            self.__create_config()
        
        self.__read_config()
        self.__validate()

    def __create_config(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)

    def __read_config(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def __validate(self):
        if not isinstance(self.config, list):
            raise ValueError('Config root must be a list of cameras')

        for cam in self.config:
            for key in ['nickname', 'username', 'password', 'ip', 'port', 'streams']:
                if key not in cam:
                    raise ValueError(f'Camera missing key: {key}')

            cam['show_in_app'] = cam.get('show_in_app', True)
            cam['rtsp_nostream'] = f"rtsp://{cam['username']}:{cam['password']}@{cam['ip']}:{cam['port']}/"