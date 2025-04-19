import os
from pathlib import Path
import yaml
import json
import cv2
import numpy as np
import traceback
from datetime import timedelta

class Configurations:

    def __init__(self, width: int, height: int, fps: int):

        self.width = width
        self.height = height
        self.fps = fps

class Foreground:

    def __init__(self, obj):

        if type(obj['text']) == list:

            # Multi-line text
            lines = obj['text']

            # Font settings
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 1
            padding = 10
            line_spacing = 10  # pixels between lines

            # Calculate max width and total height
            line_sizes = [cv2.getTextSize(line, font, font_scale, thickness) for line in lines]
            line_widths = [w for (w, h), base in line_sizes]
            line_heights = [h for (w, h), base in line_sizes]

            max_width = max(line_widths)
            total_height = sum(line_heights) + (len(lines) - 1) * line_spacing

            # Final image size with padding
            img_width = max_width + 2 * padding
            img_height = total_height + 2 * padding

            # Create blank image
            img = np.zeros((img_height, img_width, 3), dtype=np.uint8)

            # Draw each line
            y = padding
            for i, line in enumerate(lines):
                (text_width, text_height), baseline = cv2.getTextSize(line, font, font_scale, thickness)
                x = padding + int((max_width - line_widths[i]) / 2)
                y += text_height
                cv2.putText(img, line, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
                y += line_spacing  # move down for next line

        else:

            # Text and font settings
            text = obj['text']
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 1

            # Get text size
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

            # Add some padding
            padding = 10
            img_width = text_width + 2 * padding
            img_height = text_height + baseline + 2 * padding

            # Create blank image (black background)
            img = np.zeros((img_height, img_width, 3), dtype=np.uint8)

            # Calculate position: baseline is at the bottom of the text
            x = padding
            y = padding + text_height

            # Put text onto image
            cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        self.img = img

class Foregrounds:

    def __init__(self, fgs, frame, confs):
    
        if type(fgs) == list:
            for obj in fgs:
                fg = Foreground(obj).img

                fh, fw = fg.shape[:2]
                x, y = frame.shape[1] // 2, frame.shape[0] // 2  # Center of frame

                # Calculate half-sizes
                h_half, w_half = fh // 2, fw // 2

                # Final slicing area
                frame[y-h_half:y-h_half+fh, x-w_half:x-w_half+fw] = fg
        else:
            obj = fgs
            fg = Foreground(obj).img

            fh, fw = fg.shape[:2]
            x, y = frame.shape[1] // 2, frame.shape[0] // 2  # Center of frame

            # Calculate half-sizes
            h_half, w_half = fh // 2, fw // 2

            # Final slicing area
            frame[y-h_half:y-h_half+fh, x-w_half:x-w_half+fw] = fg

        self.frame = frame

class Clip:

    def __init__(self, confs, between, foregrounds, audio, subtitle):
        
        self.frames = []
        _from = map(int, between[0].split(":"))
        _to = map(int, between[1].split(":"))
        frames = int((timedelta(*_to) - timedelta(*_from)).total_seconds()) * confs.fps

        center = ()
        for i in range(0, frames):
            frame = np.zeros((confs.height, confs.width, 3), dtype=np.uint8)
            self.frames.append(Foregrounds(foregrounds, frame, confs).frame)
            

class Clips:

    def __init__(self, out_path, confs, clips):
        
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use mp4v codec - more compatible
            out = cv2.VideoWriter(out_path, fourcc, confs.fps, (confs.width, confs.height)) # Define dimensions

            frames = []
            for clip in clips:
                frames += Clip(confs, **clip).frames

            for frame in frames:
                out.write(frame)

            out.release()
            cv2.destroyAllWindows()  # Close OpenCV windows
            print(f"Video created successfully at: {out_path}")

        except Exception as e:
            print(f"An error occurred: {e} ")
            traceback.print_exc()

class Video_as_Yaml:

    def __init__(self, file):
        
        if os.path.exists(file):
            # Making Temp Dir
            inp_path = Path(file)
            temp_dir = f"{inp_path.stem}.temp"
            os.makedirs(temp_dir, exist_ok=True)
            # Parsing
            with open(inp_path, 'r') as f:
                self.data = yaml.safe_load(f)
            # Processing
            keys = self.data.keys()
            if 'confs' in keys:
                confs = Configurations(**self.data['confs'])
            else:
                confs = Configurations(width=640, height=360, fps=20)

            if 'clips' in keys:
                Clips(f"{inp_path.stem}.mp4", confs, self.data['clips'])

            print(json.dumps(self.data, indent=2, sort_keys=True))
        else:
            print(f"Error: File not found: {file}")

if __name__ == '__main__':

    Video_as_Yaml('demo.yaml')