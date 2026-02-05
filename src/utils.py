import loggerric as lr
import sys, os

def resource_path(target_path:str):
    """
    **Get full path from relative path. Compilation safe!**

    *Parameters*:
    - `target_path` (str): Path to target
    """

    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), target_path)

    return os.path.join(os.path.dirname(__file__), target_path)