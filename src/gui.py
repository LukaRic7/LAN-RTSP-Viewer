from PIL import Image, ImageTk
from tkinter import ttk
import loggerric as lr
import tkinter as tk
import cv2, time

from stream_pipeline import StreamPipeline
import filters

class Gui(tk.Frame):
    """**Main Tkinter GUI**"""

    FILTER_MAP = {
        'Raw': filters.Raw,
        'Motion': filters.Motion,
        'Edges': filters.CannyEdge
    }

    def __init__(self, root:tk.Tk, config:list[dict]):
        lr.Log.debug('Initializing GUI...')

        super().__init__(root)

        self.root = root
        self.config = config

        self.dynamic_cams = {}

        self.__build_ui()
        self.__render_loop()

    def __build_ui(self):
        self.grid_rowconfigure(index=1, weight=1)
        self.grid_columnconfigure(index=0, weight=1)

        button_frame = tk.Frame(self)
        button_frame.grid(row=0, column=0, sticky='new')

        canvas_frame = tk.Frame(self)
        canvas_frame.grid(row=1, column=0, sticky='nsew')

        for i in range(len(self.config)):
            button_frame.grid_columnconfigure(index=i, weight=1)
            canvas_frame.grid_columnconfigure(index=i, weight=1)
        canvas_frame.grid_rowconfigure(index=1, weight=1)

        for index, cam_data in enumerate(self.config):
            if not cam_data['show_in_app']:
                continue
    
            nickname = cam_data['nickname']

            lr.Log.debug(f'Inserting Camera: {nickname}')

            sub_frame = tk.LabelFrame(button_frame, text=nickname)
            sub_frame.grid(row=0, column=index, padx=5, sticky='nsew')
            sub_frame.grid_columnconfigure(index=[2, 4], weight=1)

            stream_var = tk.StringVar(value=list(cam_data['streams'].keys())[0])
            stream_menu = ttk.Combobox(sub_frame, textvariable=stream_var, values=list(cam_data['streams'].keys()), state='readonly', width=8)

            tk.Label(sub_frame, text='Feed:', anchor='center').grid(row=0, column=1, padx=(0, 1), pady=(0, 5), sticky='nsew')

            footage_var = tk.StringVar(value=list(self.FILTER_MAP.keys())[0])
            footage_menu = ttk.Combobox(sub_frame, textvariable=footage_var, values=list(self.FILTER_MAP.keys()), state='readonly', width=8)

            tk.Label(sub_frame, text='Quality:', anchor='center').grid(row=0, column=3, padx=(0, 1), pady=(0, 5), sticky='nsew')

            fps_var = tk.StringVar(value='15')
            fps_menu = ttk.Combobox(sub_frame, textvariable=fps_var, values=[5, 15, 30, 60], state='readonly', width=3)

            tk.Label(sub_frame, text='FPS:', anchor='center').grid(row=0, column=5, padx=(0, 1), pady=(0, 5), sticky='nsew')

            button = tk.Button(sub_frame, text='Connect', width=12,
                            command=lambda c=cam_data, s=stream_var, f=footage_var, fps=fps_var, n=nickname: self._toggle_camera(c, s, f, fps, n))
            
            button.grid(row=0, column=0, padx=5, pady=(0, 5), sticky='nsew')
            footage_menu.grid(row=0, column=2, padx=5, pady=(0, 5), sticky='nsew')
            stream_menu.grid(row=0, column=4, padx=5, pady=(0, 5), sticky='nsew')
            fps_menu.grid(row=0, column=6, padx=5, pady=(0, 5), sticky='nsew')

            canvas = tk.Canvas(canvas_frame, width=480, height=270, bg='black')
            canvas.grid(row=1, column=index, padx=2, pady=2, sticky='nsew')

            self.dynamic_cams[nickname] = {
                "camera": cam_data,
                "canvas": canvas,
                "stream_var": stream_var,
                "footage_var": footage_var,
                'footage_menu': footage_menu,
                'stream_menu': stream_menu,
                'fps_menu': fps_menu,
                "fps_var": fps_var,
                "button": button,
                "pipeline": None,
                "last_render_ts": 0  # Added to track FPS
            }

    def _toggle_camera(self, cam_data, stream_var, footage_var, fps_var, nickname):
        dyn = self.dynamic_cams[nickname]
        if dyn['pipeline'] and dyn['pipeline'].running:
            lr.Log.debug(f'Disabling camera: {nickname}')
            dyn['pipeline'].stop()
            dyn['pipeline'] = None
            dyn['canvas'].delete("all")
            dyn['button'].configure(text="Connect")
            dyn['footage_menu'].configure(state='enabled')
            dyn['stream_menu'].configure(state='enabled')
            dyn['fps_menu'].configure(state='enabled')
        else:
            lr.Log.debug(f'Enabling camera: {nickname}')
            selected_filter_name = footage_var.get()
            filter_instance = self.FILTER_MAP.get(selected_filter_name, filters.Raw)()
            pipeline = StreamPipeline(
                cam_data,
                stream_var.get(),
                dyn['canvas'],
                fps=int(fps_var.get()), 
                filter_func=filter_instance
            )

            pipeline.start()
            dyn['pipeline'] = pipeline
            dyn['last_render_ts'] = 0 # Reset timer
            dyn['button'].configure(text="Disconnect")
            dyn['footage_menu'].configure(state='disabled')
            dyn['stream_menu'].configure(state='disabled')
            dyn['fps_menu'].configure(state='disabled')

    def __render_loop(self):
        """Render latest frames for all active cameras based on individual FPS settings."""

        current_time = time.time()

        for dyn in self.dynamic_cams.values():
            pipeline = dyn['pipeline']
            canvas = dyn['canvas']
            
            if pipeline and pipeline.running:
                # Figure the target FPS
                try:
                    target_fps = int(dyn['fps_var'].get())
                except ValueError: 
                    target_fps = 15
                    
                interval = 1.0 / target_fps
                
                # Only update if enough time has passed based on selected FPS
                if current_time - dyn['last_render_ts'] < interval:
                    continue

                # Update timestamp
                dyn['last_render_ts'] = current_time

                frame, motion_boxes = pipeline.get_frame()
                
                # Check for stale frame
                if frame is None or (current_time - pipeline.last_frame_time > 2):
                    canvas.delete("all")
                    canvas.create_text(
                        canvas.winfo_width()//2,
                        canvas.winfo_height()//2,
                        text="ERROR: NO FEED",
                        fill="red",
                        font=("Arial", 20)
                    )
                else:
                    # Draw motion boxes if any
                    display_frame = frame.copy()
                    for x,y,w,h in motion_boxes:
                        cv2.rectangle(display_frame, (x,y), (x+w,y+h), (0,255,0), 2)

                    canvas_w = canvas.winfo_width()
                    canvas_h = canvas.winfo_height()
                    
                    src_w, src_h = pipeline.get_resolution()
                    
                    if src_w == 0 or src_h == 0: 
                        # Fallback if frame read but resolution not set yet
                        src_h, src_w = display_frame.shape[:2]

                    scale_w = canvas_w / src_w
                    scale_h = canvas_h / src_h
                    
                    # Take smallest scale to fit, BUT clamp at 1.0 to prevent upscaling
                    scale = min(scale_w, scale_h, 1.0)
                    
                    new_w, new_h = int(src_w * scale), int(src_h * scale)
                    
                    # Only resize if necessary (optimization)
                    if new_w != src_w or new_h != src_h:
                        resized = cv2.resize(display_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    else:
                        resized = display_frame

                    img = ImageTk.PhotoImage(Image.fromarray(resized))
                    canvas.image = img
                    canvas.delete("all")
                    
                    # Center the image
                    x_pos = (canvas_w - new_w) // 2
                    y_pos = (canvas_h - new_h) // 2
                    canvas.create_image(x_pos, y_pos, anchor="nw", image=img)

        # Run loop faster to accommodate high FPS settings
        self.after(10, self.__render_loop)