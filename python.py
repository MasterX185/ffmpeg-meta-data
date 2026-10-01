"""Zeigt ausführliche, übersichtlich gruppierte Medienmetadaten mit ffprobe an."""

import json
import os
import shutil
import subprocess
from fractions import Fraction


def extract_metadata(file_path):
    """Liest Format-, Stream- und Kapitelinformationen mit ffprobe aus."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            "-of", "json",
            file_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def format_duration(value):
    """Wandelt Sekunden in Stunden, Minuten und Sekunden um."""
    try:
        total_seconds = float(value)
    except (TypeError, ValueError):
        return str(value) if value else "unbekannt"

    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02} ({total_seconds:.3f} s)"


def format_rate(value):
    """Formatiert ffprobe-Bruchraten, zum Beispiel als Bilder pro Sekunde."""
    try:
        rate = float(Fraction(value))
    except (ValueError, ZeroDivisionError, TypeError):
        return str(value) if value and value != "0/0" else "unbekannt"
    return f"{rate:.3f}"


def print_tags(tags, indent="  "):
    if not tags:
        return
    print(f"{indent}Tags:")
    for key, value in tags.items():
        print(f"{indent}  {key}: {value}")


def print_stream(stream, index):
    stream_type = stream.get("codec_type", "Sonstiger")
    kind = {
        "video": "Bild-/Videostream",
        "audio": "Audiostream",
        "subtitle": "Untertitelstream",
        "data": "Datenstream",
        "attachment": "Anhang",
    }.get(stream_type, f"Stream ({stream_type})")

    print(f"\n{kind} {index + 1}")
    details = [
        ("Codec", "codec_name"),
        ("Profil", "profile"),
        ("Codec-Beschreibung", "codec_long_name"),
        ("Sprache", None),
        ("Dauer", "duration"),
        ("Bitrate", "bit_rate"),
    ]
    for label, key in details:
        value = stream.get(key) if key else stream.get("tags", {}).get("language")
        if value:
            if label == "Dauer":
                value = format_duration(value)
            elif label == "Bitrate":
                value = f"{int(value):,} bit/s".replace(",", ".")
            print(f"  {label}: {value}")

    if stream_type == "video":
        width = stream.get("width")
        height = stream.get("height")
        if width and height:
            print(f"  Auflösung: {width} x {height} Pixel")
        video_details = [
            ("Bildrate", "avg_frame_rate", " fps"),
            ("Nominale Bildrate", "r_frame_rate", " fps"),
            ("Pixel-Format", "pix_fmt", ""),
            ("Seitenverhältnis", "display_aspect_ratio", ""),
            ("Abtastverhältnis", "sample_aspect_ratio", ""),
            ("Farbbereich", "color_range", ""),
            ("Farbmatrix", "color_space", ""),
            ("Farbübertragung", "color_transfer", ""),
            ("Farbprimärfarben", "color_primaries", ""),
            ("Feldreihenfolge", "field_order", ""),
        ]
        printed = set()
        for label, key, suffix in video_details:
            value = stream.get(key)
            if value and (label, key) not in printed:
                if key in ("avg_frame_rate", "r_frame_rate"):
                    value = format_rate(value)
                print(f"  {label}: {value}{suffix}")
                printed.add((label, key))
    elif stream_type == "audio":
        for label, key, suffix in (
            ("Abtastrate", "sample_rate", " Hz"),
            ("Kanäle", "channels", ""),
            ("Kanalanordnung", "channel_layout", ""),
            ("Sample-Format", "sample_fmt", ""),
        ):
            value = stream.get(key)
            if value:
                print(f"  {label}: {value}{suffix}")

    print_tags(stream.get("tags"))


def print_metadata(file_path, metadata):
    file_info = os.stat(file_path)
    media_format = metadata.get("format", {})
    print("\n" + "=" * 64)
    print(f"Datei: {os.path.basename(file_path)}")
    print("=" * 64)
    print("\nDatei und Container")
    print(f"  Pfad: {file_path}")
    print(f"  Dateigröße: {file_info.st_size:,} Byte".replace(",", "."))
    if media_format.get("format_long_name"):
        print(f"  Format: {media_format['format_long_name']}")
    if media_format.get("format_name"):
        print(f"  Formatkennung: {media_format['format_name']}")
    if media_format.get("duration"):
        print(f"  Gesamtdauer: {format_duration(media_format['duration'])}")
    if media_format.get("bit_rate"):
        bitrate = int(media_format["bit_rate"])
        print(f"  Durchschnittliche Bitrate: {bitrate:,} bit/s".replace(",", "."))

    print_tags(media_format.get("tags"), indent="  ")

    streams = metadata.get("streams", [])
    for index, stream in enumerate(streams):
        print_stream(stream, index)

    chapters = metadata.get("chapters", [])
    if chapters:
        print(f"\nKapitel ({len(chapters)})")
        for index, chapter in enumerate(chapters, start=1):
            start = format_duration(chapter.get("start_time"))
            end = format_duration(chapter.get("end_time"))
            title = chapter.get("tags", {}).get("title", "Ohne Titel")
            print(f"  {index}. {start} bis {end}: {title}")
            print_tags(chapter.get("tags"), indent="    ")

    if not streams:
        print("\nKeine Audio-, Bild- oder Videostreams gefunden.")
        
def save_metadata_to_json(file_path, metadata):
    """Speichert die Metadaten in einer JSON-Datei."""
    json_file_path = f"{file_path}.metadata.json"
    try:
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(metadata, json_file, ensure_ascii=False, indent=4)
        print(f"\nMetadaten wurden in '{json_file_path}' gespeichert.")
    except IOError as e:
        print(f"\nFehler beim Speichern der Metadaten: {e}")


def main():
    if not shutil.which("ffprobe"):
        print("ffprobe wurde nicht gefunden. Bitte installiere FFmpeg inklusive ffprobe.")
        return

    while True:
        file_path = input("Pfad zur Bild- oder Videodatei (leer oder q zum Beenden): ").strip()
        if not file_path or file_path.lower() == "q":
            break

        file_path = os.path.abspath(os.path.expanduser(file_path.strip('"')))
        if not os.path.isfile(file_path):
            print(f"Datei nicht gefunden: {file_path}\n")
            continue

        try:
            metadata = extract_metadata(file_path)
            print_metadata(file_path, metadata)
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or "Unbekannter ffprobe-Fehler"
            print(f"Metadaten konnten nicht gelesen werden: {message}")
        except (OSError, json.JSONDecodeError) as error:
            print(f"Fehler beim Lesen der Metadaten: {error}")
            
        save_metadata_to_json(file_path, metadata)


if __name__ == "__main__":
    main()