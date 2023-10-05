import json
from sys import exit, stderr
from pytube import YouTube, Search
from pytube.exceptions import *
from dotenv import load_dotenv
import os
import base64
from requests import post, get
import re
from mutagen.mp4 import MP4, MP4Cover
from ytmusicapi import YTMusic

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")


def main():
    token = get_token()
    url = input("Enter a URL: ")
    youtube_pattern = re.compile(r'.*(youtube\.com|youtu\.be).*')
    spotify_pattern = re.compile(r'(https://)?open\.spotify\.com/(track|playlist)/(\w+)(\?si=\w+)?')

    if re.findall(youtube_pattern, url):
        song_id = get_song_id(token, url)
        download_video(url, song_id)
        return

    song_id = spotify_pattern.sub(r'\3', url)
    if song_id:
        data = get_metadata(token, song_id)
        title = data[1]
        artist = data[0]["artists"][0]["name"]
        search_query = f"{title} {artist}"
        print(search_query)
        ytmusic = YTMusic()
        search = ytmusic.search(search_query, limit=1, filter="songs")
        video_id = search[0]["videoId"]
        query_url = f"https://www.youtube.com/watch?v={video_id}"
        print(query_url)
        download_video(query_url, song_id)


def download_video(url, song_id):
    token = get_token()
    try:
        video = YouTube(url.strip())
    except RegexMatchError:
        stderr.write("Invalid URL\n")
        exit(1)
    except VideoUnavailable:
        stderr.write("Video not available\n")
        exit(1)
    stream = video.streams.get_audio_only()

    # TODO: Add a downloading status bar
    print(f"Downloading from {url}")
    title = stream.title.replace(" ", "_") + ".m4a"
    filepath = stream.download("/home/sh/Downloads", title)
    print("Download complete!")
    data = get_metadata(token, song_id)
    add_metadata(filepath, data)


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
    json_result = json.loads(result.content)["album"], json.loads(result.content)["name"], json.loads(result.content)[
        "artists"]
    return json_result


def get_song_id(token, url):
    video = YouTube(url)
    # Fetches the track and artist names from the YouTube video
    track = video.title.replace(" ", "%20")
    artist = video.author.replace(" ", "%20")
    # Spotify search API call which returns 1 track
    query_url = f"https://api.spotify.com/v1/search?q=track:{track}%20artist:{artist}&type=track&limit=1"
    headers = get_auth_header(token)
    result = get(query_url, headers=headers)
    # Gets the song id from the JSON object
    json_result = json.loads(result.content)["tracks"]["items"][0]
    song_id = json_result["id"]
    return song_id


def add_metadata(filepath, data):
    mp4 = MP4(filepath)

    # Retrieving metadata from Spotify's API
    name = data[1]
    album = data[0]["name"]
    artist = data[0]["artists"][0]["name"]
    cover_url = data[0]["images"][0]["url"]

    # Downloading cover art
    response = get(cover_url)
    image = response.content
    cover_path = f"/home/sh/Downloads/CoverArt/{album}{artist}.jpeg".replace(" ", "_")
    with open(cover_path, "wb") as file:
        file.write(image)

    # Creating an album cover object
    album_cover = MP4Cover(open(cover_path, "rb").read(), imageformat=MP4Cover.FORMAT_JPEG)

    # Writing metadata into the file
    mp4["\xa9nam"] = name
    mp4["\xa9alb"] = album
    mp4["\xa9ART"] = artist
    with open(cover_path, "rb") as coverart:
        mp4["covr"] = [MP4Cover(coverart.read(), imageformat=MP4Cover.FORMAT_JPEG)]

    mp4.save(filepath)
    mp4.pprint()


if __name__ == '__main__':
    main()
