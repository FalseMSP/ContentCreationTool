import os
import pickle
from moviepy import VideoFileClip, AudioFileClip
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Constants
DIRECTORY = 'C:/Users/markp/Documents/AutoamtedShorts/Shorts/'  # Fixed: trailing slash
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
DESCRIPTION = "Redlife/Bluelife does impressive Omen outplays to get free kills"
TAGS = ["Omen Outplay", "Flick", "Valorant", "Valorant Ace", "Valorant 5k", "Valorant 6k"]
TRIM_FRONT = 0  # Seconds
TRIM_END = 0    # Seconds


def delete_all_files(directory):
    """Delete all files in the specified directory."""
    if not os.path.isdir(directory):
        raise ValueError(f"The directory {directory} does not exist or is not a directory.")

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
        else:
            print(f"Skipped non-file item: {file_path}")


def get_authenticated_service():
    """Load OAuth 2.0 credentials and return an authenticated YouTube service."""
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)


def upload_video(service, file_name, title, description, tags, category_id):
    """Upload a video to YouTube."""
    request_body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': 'unlisted'
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
    """Extract the filename without extension from a path."""
    filename_with_extension = os.path.basename(path)
    title, _ = os.path.splitext(filename_with_extension)
    return title


def crop_and_shortify(input_path, output_path, start_trim_seconds, end_trim_seconds, audio_path=None):
    """Crop video to 9:16 aspect ratio, trim it, and optionally add background audio."""

    # Load the video
    video = VideoFileClip(input_path)
    duration = video.duration

    # Force duration to be under 60 seconds (YouTube Shorts limit)
    if duration > 59 + start_trim_seconds + end_trim_seconds:
        start_trim_seconds = duration - end_trim_seconds - 59

    start_time = start_trim_seconds
    end_time = duration - end_trim_seconds

    if end_time < start_time:
        raise ValueError("End trim time is before start trim time. Adjust the trim seconds.")

    # Trim the video — moviepy 2.x uses subclipped()
    trimmed_video = video.subclipped(start_time, end_time)

    # Calculate crop dimensions for 9:16 aspect ratio
    target_aspect_ratio = 9 / 16
    original_width, original_height = trimmed_video.size

    if original_width / original_height > target_aspect_ratio:
        # Wider than 9:16 — crop the sides
        new_width = int(original_height * target_aspect_ratio)
        new_height = original_height
        x1 = (original_width - new_width) // 2
        x2 = x1 + new_width
        y1, y2 = 0, new_height
    else:
        # Taller than 9:16 — crop top/bottom
        new_width = original_width
        new_height = int(original_width / target_aspect_ratio)
        x1, x2 = 0, new_width
        y1 = (original_height - new_height) // 2
        y2 = y1 + new_height

    # moviepy 2.x uses cropped() instead of crop()
    cropped_video = trimmed_video.cropped(x1=x1, x2=x2, y1=y1, y2=y2)

    # Resize to 1080x1920 — moviepy 2.x uses resized()
    target_width = 1080
    target_height = int(target_width * (16 / 9))
    scaled_video = cropped_video.resized((target_width, target_height))

    # Add background music if provided
    if audio_path:
        audio = AudioFileClip(audio_path)
        # Apply volume reduction and duration — moviepy 2.x uses multiply_volume() and with_duration()
        audio = audio.multiply_volume(0.3).with_duration(scaled_video.duration)
        final_video = scaled_video.with_audio(audio)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    else:
        scaled_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    # Clean up clips to release file handles
    video.close()
    trimmed_video.close()
    cropped_video.close()
    scaled_video.close()

    return scaled_video


def scan_directory(directory_path):
    """Recursively scan a directory for video files."""
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
    file_list = []

    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext.lower() in video_extensions:
                file_path = os.path.join(root, file_name)
                file_list.append(file_path)

    return file_list


if __name__ == '__main__':
    file_list = scan_directory(DIRECTORY)
    print(f"Found {len(file_list)} video(s): {file_list}")

    service = get_authenticated_service()  # Authenticate once, reuse for all uploads

    for file in file_list:
        file_name = get_file_title(file)
        output_path = os.path.join(DIRECTORY, f"{file_name}Shortified.mp4")  # Fixed: proper path join

        print(f"Processing: {file}")
        crop_and_shortify(file, output_path, TRIM_FRONT, TRIM_END)

        print(f"Uploading: {output_path}")
        upload_video(service, output_path, file_name, DESCRIPTION, TAGS, 20)

    print("All videos processed.")
    print("Deleting files...")
    delete_all_files(DIRECTORY)
    print("Done.")