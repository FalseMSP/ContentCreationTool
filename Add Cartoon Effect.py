import os
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import resize, crop
import google.auth
import httplib2
import pickle
from sklearn.cluster import KMeans
import cv2
import numpy as np
from multiprocessing import Pool


# Constants
DIRECTORY = 'C:/Users/CPSEGuest/Videos/Captures/'
colors = [
    [255, 182, 193],  # Light Pink
    [255, 239, 179],  # Pastel Yellow
    [176, 224, 230],  # Powder Blue
    [152, 251, 152],  # Pale Green
    [255, 228, 225],  # Misty Rose
    [255, 240, 245],  # Lavender Blush
    [240, 248, 255],  # Alice Blue
    [255, 224, 178],  # Peach Puff
    [219, 219, 255],  # Periwinkle
    [255, 204, 229],  # Cotton Candy
    [255, 192, 203],  # Pink
    [200, 191, 231],  # Lavender
    [190, 255, 255],  # Light Cyan
    [240, 230, 140],  # Khaki
    [255, 240, 245],  # Lavender Blush
    [255, 239, 213],  # Blanched Almond
    [240, 255, 240],  # Honeydew
    [248, 248, 255],  # Ghost White
    [248, 222, 126],  # Light Goldenrod Yellow
    [245, 245, 245],  # White Smoke
    [255, 218, 185],  # Antique White
    [255, 228, 196],  # Bisque
    [255, 239, 196],  # Light Cream
    [255, 240, 200],  # Cream
    [200, 255, 200],  # Honeydew
    [255, 240, 245],  # Lavender Blush
    [135, 206, 250],  # Light Sky Blue
    [147, 112, 219],  # Medium Purple
    [255, 240, 245],  # Lavender Blush
    [205, 133, 63],   # Peru
    [255, 182, 193],  # Light Pink
    [255, 248, 220],  # Cornsilk
    [224, 255, 255],  # Light Cyan
    [240, 230, 140],  # Khaki
    [240, 248, 255],  # Alice Blue
    [253, 245, 230],  # Old Lace
    [255, 228, 225],  # Misty Rose
    [240, 255, 240],  # Honeydew
    [255, 228, 196],  # Bisque
    [105, 105, 105],  # Dim Gray
    [169, 169, 169],  # Dark Gray
    [112, 128, 144],  # Slate Gray
    [47, 79, 79],     # Dark Slate Gray
    [139, 0, 0],      # Dark Red
    [139, 69, 19],    # Saddle Brown
    [128, 0, 0],      # Maroon
    [0, 0, 128],      # Navy
    [0, 100, 0],      # Dark Green
    [25, 25, 112],    # Midnight Blue
    [128, 128, 128],  # Gray
    [85, 107, 47],    # Dark Olive Green
    [139, 0, 139],    # Dark Violet
    [75, 0, 130],     # Indigo
    [0, 0, 139],      # Dark Blue
    [139, 0, 139],    # Dark Violet
    [50, 50, 50],     # Charcoal
    [95, 158, 160],   # Cadet Blue
    [0, 0, 0],        # Black
    [75, 0, 130],     # Indigo
    [64, 64, 64],     # Dark Gray
]

def get_file_title(path):
    filename_with_extension = os.path.basename(path)
    title, _ = os.path.splitext(filename_with_extension)
    return title

def find_closest_colors(pixels, colors):
    colors = np.array(colors)
    pixel_colors_diff = pixels[:, np.newaxis, :] - colors
    distances = np.sum(pixel_colors_diff ** 2, axis=2)
    closest_color_indices = np.argmin(distances, axis=1)
    return colors[closest_color_indices]

def process_frame(image):
    global colors

    # Convert image to float32 for precision
    image_float = image.astype(np.float32)
    pixels = image_float.reshape(-1, 3)
    processed_pixels = find_closest_colors(pixels, colors)
    processed_image = processed_pixels.reshape(image.shape).astype(np.uint8)
    cv2.blur(processed_image,(7,7))

    # Convert to grayscale for edge detection
    gray_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_image, 100, 200)

    # Create an outline image
    outline_image = np.zeros_like(processed_image)
    outline_image[edges != 0] = [0, 0, 0]  # Black outline

    # Combine the processed image and the outline
    combined_image = cv2.addWeighted(processed_image, 1, outline_image, 1, 0)

    return combined_image

def process_video(input_path, output_path):
    clip = VideoFileClip(input_path)
    processed_clip = clip.fl_image(process_frame)
    processed_clip.write_videofile(output_path, codec='libx264')

def scan_directory(directory_path):
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
    file_list = []
    
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext.lower() in video_extensions:
                file_path = os.path.join(root, file_name)
                file_list.append(file_path)
    
    return file_list

if __name__ == "__main__":
    file_list = scan_directory(DIRECTORY)
    print(file_list)
    for file in file_list:
        fileName = get_file_title(file)
        input_video = file  # Path to the input video file
        output_video = f"{DIRECTORY}{fileName}Cartoonified.mp4"  # Path to the output video file
        process_video(input_video, output_video)