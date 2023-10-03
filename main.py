import json
from sys import exit, stderr
from pytube import YouTube, Search
from pytube.exceptions import *
from dotenv import load_dotenv
import os
import base64
from requests import post, get
import re
import mutagen.id3

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")


def main():
    token = get_token()
    url = input("Enter a URL: ")
    youtube_pattern = re.compile(r'.*(youtube\.com|youtu\.be).*')
    spotify_pattern = re.compile(r'(https://)?open\.spotify\.com/(track|playlist)/(\w+)(\?si=\w+)?')

    if re.findall(youtube_pattern, url):
        get_video(url)
        return

    song_id = spotify_pattern.sub(r'\3', url)
    if song_id:
        data = get_metadata(token, song_id)
        title = data[1]
        artist = data[0]["artists"][0]["name"]
        search_query = f"{title} {artist} topic"
        search = Search(search_query)
        video_renderer = search.fetch_query()["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
            "sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"][0]["videoRenderer"]
        video_id = video_renderer["videoId"]
        query_url = f"https://www.youtube.com/watch?v={video_id}"
        get_video(query_url)


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
    # TODO: Add a downloading status bar
    print("Downloading...")
    title = stream.title.replace(" ", "_") + ".m4a"
    stream.download("/home/sh/Downloads", title)
    print("Download complete!")


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
    json_result = json.loads(result.content)["album"], json.loads(result.content)["name"]
    return json_result


# TODO - Add metadata to downloaded song
def add_metadata():
    print("placeholder")


if __name__ == '__main__':
    main()
