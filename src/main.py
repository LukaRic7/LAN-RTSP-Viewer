from tkinter import Tk
import loggerric as lr

from config import ConfigParser
from gui import Gui

VERSION = 2.0

# Ensure the file is not imported
if __name__ == '__main__':
    lr.Log.info('Initializing...')

    # Initialize a window
    root = Tk()
    root.title(f'LAN RTSP Viewer v{VERSION}')

    # Open the config
    config_parser = ConfigParser('streams.json')

    # Create the GUI
    app = Gui(root, config_parser.config)
    app.pack(fill='both', expand=True)

    # Set the minimum size
    app.update()
    root.wm_minsize(app.winfo_width(), app.winfo_height())

    # Launch off!
    root.mainloop()