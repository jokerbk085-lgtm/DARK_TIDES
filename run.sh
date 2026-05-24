#!/usr/bin/env bash
cd "$(dirname "$0")"
for f in input/*.mp3 input/*.wav input/*.m4a; do
    [ -f "$f" ] && python main.py "$f" "$@" && exit 0
done
echo "هیچ فایل صوتی در input/ پیدا نشد."
