from sys import exit, stderr
from pytube import YouTube
from pytube.exceptions import *

url = input("Enter a URL (YouTube only): ")

try:
    video = YouTube(url.strip())
except RegexMatchError:
    stderr.write("Invalid URL\n")
    exit(1)
except VideoUnavailable:
    stderr.write("Video not available\n")
    exit(1)

stream = video.streams.get_audio_only()
print(stream.title)
title = stream.title.replace(" ", "_") + ".m4a"
stream.download("/home/sh/Downloads", title)

# TODO - Add metadata to downloaded song
