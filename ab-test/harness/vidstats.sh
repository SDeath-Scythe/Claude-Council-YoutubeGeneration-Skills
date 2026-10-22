#!/usr/bin/env bash
# usage: vidstats.sh <video.mp4> <out_prefix>  — duration/size/loudness + 4x4 contact sheet
v="$1"; o="$2"
ffprobe -v error -show_entries format=duration,size:stream=codec_type,width,height,r_frame_rate -of compact "$v"
ffmpeg -hide_banner -nostats -i "$v" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|LRA:|Peak:)" | tr -s ' '
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v")
ffmpeg -hide_banner -loglevel error -y -i "$v" -vf "fps=16/$d,scale=480:-1,tile=4x4:padding=6:color=black" -frames:v 1 "${o}_contact.jpg"
echo "sheet: ${o}_contact.jpg"
