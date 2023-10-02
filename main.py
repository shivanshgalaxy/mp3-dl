import json
from sys import exit, stderr
from pytube import YouTube
from pytube.exceptions import *
from dotenv import load_dotenv
import os
import base64
from requests import post, get
import re

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")


def main():
    token = get_token()
    url = input("Enter a URL: ")
    # TODO: add regex match for YouTube/Spotify
    youtube_pattern = re.compile(r'.*(youtube\.com|youtu\.be).*')
    spotify_pattern = re.compile(r'(https://)?open\.spotify\.com/(track|playlist)/(\w+)(\?si=\w+)?')

    if re.findall(youtube_pattern, url):
        get_video(url)
        return

    song_id = spotify_pattern.sub(r'\3', url)
    if song_id:
        get_metadata(token, song_id)


def get_video(url):
    try:
        video = YouTube(url.strip())
    except RegexMatchError:
        stderr.write("Invalid URL\n")
        exit(1)
    except VideoUnavailable:
        stderr.write("Video not available\n")
        exit(1)
    stream = video.streams.get_audio_only()
    download_video(stream)


def download_video(stream):
    title = stream.title.replace(" ", "_") + ".m4a"
    stream.download("/home/sh/Downloads", title)


def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def get_metadata(token, song_id):
    url = "https://api.spotify.com/v1/tracks/" + song_id
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["album"]
    return json_result


# TODO - Add metadata to downloaded song
if __name__ == '__main__':
    main()
