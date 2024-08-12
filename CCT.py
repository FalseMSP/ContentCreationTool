import os
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import resize, crop
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import httplib2
import pickle



# Constants
DIRECTORY = 'C:/Users/CPSEGuest/Videos/Captures/'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
DESCRIPTION = "Redlife/Bluelife does impressive Omen outplays to get free kills" # a
TAGS = ["Omen Outplay", "Flick", "Valorant", "Valorant Ace", "Valorant 5k", "Valorant 6k"] # a
TRIM_FRONT = 0 # Seconds
TRIM_END = 30 # Seconds

# Delete
def delete_all_files(directory):
    """
    Delete all files in the specified directory.

    Parameters:
    - directory (str): Path to the directory from which files should be deleted.
    """
    # Ensure the directory exists
    if not os.path.isdir(directory):
        raise ValueError(f"The directory {directory} does not exist or is not a directory.")
    
    # Iterate over all items in the directory
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # Check if the item is a file and delete it
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
        else:
            print(f"Skipped non-file item: {file_path}")

# Load OAuth 2.0 credentials
def get_authenticated_service():
    creds = None
    # Token file to store the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

# Upload a video to YouTube
def upload_video(service, file_name, title, description, tags, category_id):
    request_body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': 'unlisted'  # Change to 'private' or 'unlisted' if desired
        }
    }
    
    media_file = MediaFileUpload(file_name, chunksize=-1, resumable=True)
    
    request = service.videos().insert(
        part='snippet,status',
        body=request_body,
        media_body=media_file
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
    
    print("Upload complete!")
    print(f"Video URL: https://www.youtube.com/watch?v={response['id']}")

def get_file_title(path):
    # Extract the filename with extension
    filename_with_extension = os.path.basename(path)
    # Split the filename and extension
    title, _ = os.path.splitext(filename_with_extension)
    return title

def crop_and_shortify(input_path, output_path, start_trim_seconds, end_trim_seconds, audio_path=None):
    # Load the video
    video = VideoFileClip(input_path)
    
    # Get the duration of the video in seconds
    duration = video.duration

    if duration > 59 + start_trim_seconds + end_trim_seconds:
        start_trim_seconds = duration - end_trim_seconds - 59 # Force it to be less than 60 seconds
    
    # Define the new start and end times for trimming
    start_time = start_trim_seconds
    end_time = duration - end_trim_seconds
    
    # Ensure the end time is not before the start time
    if end_time < start_time:
        raise ValueError("End trim time is before start trim time. Adjust the trim seconds.")
    
    # Trim the video
    trimmed_video = video.subclip(start_time, end_time)
    
    # Define target aspect ratio (9:16)
    target_aspect_ratio = 9 / 16
    
    # Get the original dimensions
    original_width, original_height = trimmed_video.size
    
    # Calculate the new dimensions to maintain the aspect ratio
    if original_width / original_height > target_aspect_ratio:
        # If the original video is wider than 9:16, crop the width
        new_width = int(original_height * target_aspect_ratio)
        new_height = original_height
        x1 = (original_width - new_width) // 2
        x2 = x1 + new_width
        y1, y2 = 0, new_height
    else:
        # If the original video is taller than 9:16, crop the height
        new_width = original_width
        new_height = int(original_width / target_aspect_ratio)
        x1, x2 = 0, new_width
        y1 = (original_height - new_height) // 2
        y2 = y1 + new_height
    
    # Crop the video to the new dimensions
    cropped_video = trimmed_video.crop(x1=x1, x2=x2, y1=y1, y2=y2)
    
    # Resize the cropped video to 9:16 frame (1080x1920 as an example)
    target_width = 1080
    target_height = int(target_width * (16 / 9))
    scaled_video = cropped_video.resize((target_width, target_height))
    
    # Add background music if provided
    if audio_path:
        # Load the audio file
        audio = AudioFileClip(audio_path)
        
        # Set the audio of the video
        final_audio = audio.set_duration(scaled_video.duration)
        video_with_audio = scaled_video.set_audio(final_audio)
        audio = audio.volumex(0.3)
        
        # Write the result to the output path
        video_with_audio.write_videofile(output_path, codec="libx264", audio_codec="aac")
    else:
        # Write the result to the output path without background music
        scaled_video.write_videofile(output_path, codec="libx264")
    
    return scaled_video

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
count = 0
if __name__ == '__main__':
    file_list = scan_directory(DIRECTORY)
    print(file_list)
    for file in file_list:
        fileName = get_file_title(file)
        crop_and_shortify(file,f"{DIRECTORY}{fileName}Shortified.mp4",TRIM_FRONT,TRIM_END)
        #Upload it to Youtube
        service = get_authenticated_service()
        upload_video(service, f"{DIRECTORY}{fileName}Shortified.mp4", fileName, DESCRIPTION, TAGS, 20)
        count += 1
    print("Completed")
    print("Deleting Files")
    delete_all_files(DIRECTORY)
    print("Done.")