import json
from sys import exit, stderr
from pytube import YouTube, Playlist
from pytube.exceptions import *
from dotenv import load_dotenv
import os
import base64
from requests import post, get
import re
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp3 import MP3
from ytmusicapi import YTMusic

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")


def main():
    token = get_token()
    url = input("Enter a URL: ")
    # TODO: Add a playlist handler
    youtube_pattern = re.compile(r'.*(youtube\.com|youtu\.be)/(\w+)?.*')
    spotify_pattern = re.compile(r'(https://)?(open\.)?spotify\.(com|link)/(track/|playlist/)+(\w+)(\?si=\w+)?')

    if youtube_pattern.sub(r'\2', url) == "playlist":
        download_youtube_playlist(token, url)
        return

    if re.findall(youtube_pattern, url):
        song_id = get_song_id(token, url)
        download_video(token, url, song_id)
        return

    if spotify_pattern.sub(r'\4', url) == "track/":
        song_id = spotify_pattern.sub(r'\5', url)
        download_song(token, song_id)

    if spotify_pattern.sub(r'\4', url) == "playlist/":
        playlist_id = spotify_pattern.sub(r'\5', url)
        download_spotify_playlist(token, playlist_id)


def download_video(token, url, song_id):
    convert = os.getenv("CONVERT")
    convert_to_mp3 = False
    if convert in ["y", "yes"]:
        convert_to_mp3 = True
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
    title = stream.title.replace(" ", "_").replace("(", "_").replace(")", "_")
    output_path = f"/home/sh/Music/"
    filepath = stream.download(output_path, title + ".m4a")
    if song_id:
        data = get_metadata(token, song_id)
        add_metadata(filepath, data)
    else:
        add_youtube_metadata(filepath, video)

    m4a_path = f"{output_path}m4a/{title}.m4a"
    os.system(f"ffmpeg -i {filepath} -c:v copy -c:a aac -hide_banner -loglevel error {m4a_path}")
    os.remove(filepath)
    print("Download complete!")
    if convert_to_mp3:
        mp3_path = f"{output_path}mp3/{title}.mp3"
        print("Converting")
        # ffmpeg command that converts a file's audio stream to mp3
        # while retaining its video stream using a variable bitrate
        os.system(f"ffmpeg -i {m4a_path} -c:v copy -c:a libmp3lame -q:a 4 -hide_banner -loglevel error {mp3_path}")
        mp3 = MP3(mp3_path)
        # Obtains the APIC frame which has no description (hence nothing after the colon) by default after conversion
        # to change it to front cover
        picture_tag = mp3.tags["APIC:"]
        picture_tag.type = 3  # Refers to mutagen.id3.PictureType.COVER_FRONT
        mp3.tags["APIC:"] = picture_tag
        mp3.save()
        print("Conversion complete!")


def download_song(token, song_id):
    data = get_metadata(token, song_id)
    title = data[1]
    artist = data[0]["artists"][0]["name"]
    search_query = f"{title} {artist}"
    print(search_query)
    ytmusic = YTMusic()
    search = ytmusic.search(search_query, limit=1, filter="songs")
    video_id = search[0]["videoId"]
    query_url = f"https://www.youtube.com/watch?v={video_id}"
    download_video(token, query_url, song_id)


def download_spotify_playlist(token, playlist_id):
    data = get_playlist(token, playlist_id)
    songs = data["tracks"]["items"]
    for song in songs:
        song_id = song["track"]["id"]
        download_song(token, song_id)


def download_youtube_playlist(token, playlist_url):
    playlist = Playlist(playlist_url)
    for url in playlist.video_urls:
        song_id = get_song_id(token, url)
        download_video(token, url, song_id)


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
    json_result = json.loads(result.content)

    with open("dump2.txt", "w") as file:
        json.dump(json_result, file)

    if json_result.get("error") is None:
        metadata = json_result["album"], json_result["name"], json_result(result.content)["artists"]
        metadata = list(metadata)
        return metadata
    else:
        return {}


def get_playlist(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)
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
    # Gets the song ID from the JSON object
    try:
        json_result = json.loads(result.content)["tracks"]["items"][0]
        song_id = json_result["id"]
    except IndexError:
        stderr.write("Song ID not found\n")
        return ""
    return song_id


def add_metadata(filepath, data):
    mp4 = MP4(filepath)
    mp4.delete()

    # Retrieving metadata from Spotify's API
    try:
        name = data[1]
    except KeyError:
        name = "Unknown track"
        stderr.write("Track name not found\n")

    try:
        album = data[0]["name"]
    except KeyError:
        album = ""
        stderr.write("Song album not found\n")

    artists = []
    try:
        for artist in data[2]:
            artists.append(artist["name"])
    except KeyError:
        artists.append("Unknown artist")
        stderr.write("Artist not found\n")

    try:
        cover_url = data[0]["images"][0]["url"]
        # Downloading cover art
        response = get(cover_url)
        image = response.content
        cover_path = f"/home/sh/Music/CoverArt/{album}{artists[0]}.jpeg".replace(" ", "_")
        with open(cover_path, "wb") as file:
            file.write(image)
        with open(cover_path, "rb") as coverart:
            mp4["covr"] = [MP4Cover(coverart.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    except KeyError or IOError:
        stderr.write("Album art not found\n")

    mp4["\xa9nam"] = name
    mp4["\xa9alb"] = album
    mp4["\xa9ART"] = artists

    mp4.save(filepath)
    mp4.pprint()


def add_youtube_metadata(filepath, video):
    mp4 = MP4(filepath)
    track_name = video.title
    cover_url = video.thumbnail_url
    print(cover_url)
    response = get(cover_url)
    image = response.content
    cover_path = f"/home/sh/Music/CoverArt/{track_name}.jpeg".replace(" ", "_")
    with open(cover_path, "wb") as file:
        file.write(image)
    with open(cover_path, "rb") as cover_art:
        mp4["covr"] = [MP4Cover(cover_art.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    mp4["\xa9nam"] = track_name
    mp4.save(filepath)


if __name__ == '__main__':
    main()
