import subprocess
from pathlib import Path
import os
import send2trash as st
import re
from datetime import datetime
import asyncio
import time
import json
import sys


import platform

class Config:
    speed_factor = 10


def _getch() -> str:
    if os.name == 'nt':
        import msvcrt
        return msvcrt.getch().decode()
    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def speed_up(videos: list) -> str:
    setpts = ""
    for i, video in enumerate(videos):
        setpts += build_trim_filter(i, video.get('start', ''), video.get('end', ''))
    return setpts


def concat(videos: list) -> str:
    cat_src =""
    index = len(videos)

    for i in range(index):
        cat_src += f"[v{i}]" 


    cat = f"{cat_src}concat=n={index}:v=1:a=0[v]"
    cat = f"{cat}"


    return cat




def checkdir(outputdir: str):
    path = os.path.join(speedup_dir, outputdir)
    if not os.path.exists(path):
        os.makedirs(path)

def isTsFile(file: str) -> bool:
    return True if '.ts' in file else False

def edit(videos: list):
    prev_input = 'y'
    while prev_input == 'y': 
        video_index = int(input("video index: ")) - 1
        start = input("start (hh/mm/ss, enter to skip): ")
        end = input("end (hh/mm/ss): ")
        # Convert timestamps from 'hh/mm/ss' to 'hh\:mm\:ss'
        start_hms = start.replace('/', '\\:')
        end_hms = end.replace('/', '\\:')

        videos[video_index]['start'] = start_hms
        videos[video_index]['end'] = end_hms

        prev_input = input("Do u wanna continue trimming? (y/n): ")
    
    return videos


def get_length(filename):

    result = subprocess.run([ffprob_fir, "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename], shell=False, text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    
    return float(result.stdout)

def get_total_duration(videos: list) -> float:
    total = 0
    time_format = "%H\\:%M\\:%S"
    for video in videos:
        video_name = video['name']
        video_length = get_length(video_name)
        start_time = video.get('start', None)
        end_time = video.get('end', None)
        if start_time and end_time:
            start = datetime.strptime(start_time, time_format)
            end = datetime.strptime(end_time, time_format)
            total += (end - start).total_seconds()
        elif start_time:
            start = datetime.strptime(start_time, time_format)
            total += video_length - (start - datetime(1900, 1, 1)).total_seconds()
        elif end_time:
            end = datetime.strptime(end_time, time_format)
            total += (end - datetime(1900, 1, 1)).total_seconds()
        else:
            total += video_length
    return total


def compare_length(videos, output) -> bool:
    total = get_total_duration(videos)
    speed = get_length(output)
    ok = abs(total - speed * Config.speed_factor) <= 120
    print(f"speed up ok! {speed}  {total}" if ok else f"somthimg is wrong, check again {speed}  {total}")
    return ok

def delete_video(videos):
    try:
        for video in videos:
            if os.path.exists(video):  # Check if the file exists
                st.send2trash(video)  # Delete the file
                print(f"File '{video}' has been deleted.")
            else:
                print(f"File '{video}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")


def _pending_deletes_path() -> str:
    return os.path.join(parent_dir, 'pending_deletes.json')


def load_pending_deletes() -> list:
    path = _pending_deletes_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_pending_deletes(items: list):
    path = _pending_deletes_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def add_pending_delete(videos: list, output: str | None, speed_factor: int | None = None):
    items = load_pending_deletes()
    before = None
    after = None
    ok = False
    sf = speed_factor if speed_factor is not None else Config.speed_factor
    if output:
        try:
            before = get_total_duration(videos)
            after = get_length(output)
            ok = abs(before - after * sf) <= 120
        except Exception:
            before, after, ok = None, None, False

    entry = {
        'videos': videos,
        'output': output,
        'outputOk': bool(ok),
        'before': before,
        'after': after,
        'speedFactor': sf
    }
    items.append(entry)
    save_pending_deletes(items)
    print(f"Added {len(videos)} file(s) to pending deletes: {output} (ok={ok})")


def process_pending_deletes():
    items = load_pending_deletes()
    if not items:
        print("No pending deletes.")
        return

    remaining = []
    for entry in items:
        videos = entry.get('videos', [])
        output = entry.get('output')
        speed_factor = entry.get('speedFactor', Config.speed_factor)

        original_speed = Config.speed_factor
        Config.speed_factor = speed_factor
        try:
            ok = compare_length(videos, output)
        except Exception as e:
            print(f"Error checking {output}: {e}")
            ok = False
        Config.speed_factor = original_speed

        if ok:
            names = [v['name'] if isinstance(v, dict) else v for v in videos]
            delete_video(names)
            print(f"Deleted pending originals for output: {output}")
        else:
            remaining.append(entry)

    save_pending_deletes(remaining)

    if remaining:
        print(f"\nAuto-deleted {len(items) - len(remaining)} file(s), {len(remaining)} file(s) has mismatch. pls inspect")
        for entry in remaining:
            print(f"  {entry.get('output') or '(no output)'}")

def build_trim_filter(index: int, start: str = '', end: str = '') -> str:
    speed_factor = Config.speed_factor
    if start and end:
        return f"[{index}:v]trim=start='{start}':end='{end}',setpts=PTS/{speed_factor}[v{index}]; "
    elif start:
        return f"[{index}:v]trim=start='{start}',setpts=PTS/{speed_factor}[v{index}]; "
    elif end:
        return f"[{index}:v]trim=end='{end}',setpts=PTS/{speed_factor}[v{index}]; "
    return f"[{index}:v]setpts=PTS/{speed_factor}[v{index}];"

    
def ask_delete(comp_result: bool, videos_dir: list, output: str | None = None):
    if not comp_result:
        return

    if output:
        add_pending_delete(videos_dir, output)
        return

    # interactive prompt fallback
    while True:
        y_n = input("Do u wanna delete original videos? (y/n): ")
        if y_n == 'y':
            names = [v['name'] if isinstance(v, dict) else v for v in videos_dir]
            delete_video(names)
            break
        elif y_n == 'n':
            add_pending_delete(videos_dir, None)
            break
        else:
            print("invalid answer, try again ")


def construct_args(videos: list) -> tuple[list, list]:
    """
    Constructs command-line arguments and a list of additional data from the provided video list.

    Args:
        videos (list): A list of dictionaries, each containing information about a video. 
                       Each dictionary may have keys like 'name', 'start', and 'end'.

    Returns:
        - A list of strings (`input_cmd`): A list of command-line arguments constructed from the video data.
        - A list (`videos`): A list of dictionary, each contains video name, start, end.
    """
    input_cmd = [f"{ffmpeg_dir}"]

    for video in videos:
        input_cmd.extend(["-i", video['name']])
    output = os.path.basename(videos[0]['name'])
    
    name_type = re.search(r'(.+)(\..+)$', output)

    fileName = name_type.group(1)
    fileType = name_type.group(2)

    fileType = fileType.replace(fileType, '.ts')

    output = fileName + fileType
    
    input_cmd.append("-filter_complex")
    setpts = speed_up(videos)
    cat = concat(videos)

    matchStreamlinkFormat = re.search(r'\] (.*)\.', output)
    if matchStreamlinkFormat is not None:
        matchStreamlinkFormat = matchStreamlinkFormat.group(1)
    else :
        matchStreamlinkFormat = 'dump'
    
    input_cmd += [f'{setpts}{cat}',"-map", '[v]',  "-r", "45" ]
    # appendList = [ "-c:v", "hevc_nvenc",
    #          "-preset:v", "p7",
    #         #  "-cq:v", "28",
    #          "-profile:v", "main",
    #          "-tier", "high",
    #          "-tune:v", 'hq',
    #          '-pix_fmt', 'yuv420p',
    #           "-bf", "4",]
    # appendList += ["-rc", "vbr"]    
    # appendList += ["-b:v", "1.5M", "-maxrate", "3M", "-bufsize", "6M"]
    # appendList += ['-multipass', "fullres"]
    # Read additional ffmpeg arguments from a txt file if it exists
    appendList = []
    args_file = os.path.join(parent_dir, "ffmpeg_args.txt")
    if not os.path.exists(args_file):
        # Create an empty file if it does not exist
        with open(args_file, "w") as f:
            pass
    else:
        with open(args_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    appendList.extend(line.split())
    # appendList += ["-g", "120"]
    # appendList += ["-rc-lookahead", "64"]
    # appendList += ['-t', '600']


    input_cmd += appendList
    checkdir(matchStreamlinkFormat)

    output_dir = f'{speedup_dir}/{matchStreamlinkFormat}/{output}'
    input_cmd.append(output_dir)
    
    for video in videos:
        video['name'] = os.path.normpath(video['name'])

    output_dir = os.path.normpath(output_dir)
    return [input_cmd, videos, output_dir] 

def clean_path(path: str) -> str:
    """Removes surrounding quotes from a path if they exist."""
    return path.strip().strip('"').strip("'")





def load_queue_file(queue_file: str) -> list[dict]:
    items = []
    if not os.path.exists(queue_file):
        return items

    current_speed = Config.speed_factor
    with open(queue_file, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue

            speed_m = re.match(r'^speed\s*=\s*(\d+)$', line, re.IGNORECASE)
            if speed_m:
                current_speed = int(speed_m.group(1))
                continue

            job = {'name': None, 'start': None, 'end': None, 'speed': current_speed, 'raw_line': raw_line}
            parts = re.findall(r'(\w+)=((?:"[^"]*"|\'[^\']*\'|\S)+)', line)
            if parts:
                for key, raw_value in parts:
                    value = raw_value.strip().strip('"').strip("'")
                    key = key.lower()
                    if key in ('f1', 'file', 'path', 'name'):
                        job['name'] = clean_path(value)
                    elif key == 'start':
                        job['start'] = value.replace('/', '\\:')
                    elif key == 'end':
                        job['end'] = value.replace('/', '\\:')
                    elif key == 'speed':
                        try:
                            job['speed'] = int(value)
                        except ValueError:
                            pass
            else:
                job['name'] = clean_path(line)

            if job['name']:
                items.append(job)
    return items


def process_queue_file(queue_file: str):
    print(f"Queue mode enabled. Watching '{queue_file}'.")
    print("Format:")
    print("  speed=10")
    print("  /path/to/video.ts start=00:00:30 end=01:00:00")
    print("  speed=50")
    print("  /path/to/video.ts")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            queue_items = load_queue_file(queue_file)
            if not queue_items:
                time.sleep(5)
                continue

            processed_indices = set()
            for i, job in enumerate(queue_items):
                if not check_exist(job['name']):
                    print(f"Queue item skipped; file does not exist: {job['name']}")
                    continue

                original_speed = Config.speed_factor
                Config.speed_factor = job['speed']

                args, videos_dir, output_dir = construct_args([job])
                print(f"Processing queue item: {job['name']}")
                result = subprocess.run(args, shell=False, text=True, stderr=subprocess.STDOUT)

                if result.returncode == 0:
                    add_pending_delete(videos_dir, output_dir, job['speed'])
                    processed_indices.add(i)
                    print(f"Added to pending deletes: {output_dir}")
                else:
                    print(f"Failed to process '{job['name']}' (return code {result.returncode}).")

                Config.speed_factor = original_speed

            if processed_indices:
                processed_raw = {queue_items[i]['raw_line'].rstrip('\n') for i in processed_indices}
                with open(queue_file, 'r', encoding='utf-8') as f:
                    remaining = [line for line in f if line.rstrip('\n') not in processed_raw]
                with open(queue_file, 'w', encoding='utf-8') as f:
                    f.writelines(remaining)

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nQueue mode stopped by user.")


def check_exist(path: str) -> bool:
    """Checks if a given path exists."""
    return os.path.exists(path) 

def get_video_paths_bulk():
    playlist = []
    while True:
        user = input("Enter files (0 to finish): ")
        if user == "0":
            break
        video_path = clean_path(user)
        if not check_exist(video_path):
            print(f"File {video_path} does not exist, please try again.")
            continue
        playlist.append(video_path)
    return playlist

def get_video_dicts_normal():
    videos = []
    while True:
        user = input(f"Enter file {len(videos)+1} location (0 to stop, 1 to end n trim): ")
        if user == "0":
            break
        if user == "1":
            if videos:
                videos = edit(videos)
            break
        video = clean_path(user)
        if not check_exist(video):
            print(f"File {video} does not exist, please try again.")
            continue
        videos.append(dict(name=video, start=None, end=None))
    return videos

def main():
    waitlist = []
    while True:
        print("\nChoose mode:")
        print("  0 - normal")
        print("  1 - bulk")
        print("  2 - queue file")
        print("  3 - auto-delete ok")
        print("  q - quit")
        key = _getch()
        print(key)

        if key == 'q':
            return

        try:
            mode = int(key)
        except ValueError:
            continue

        if mode == 2:
            print("Proceed? (y/n): ", end='', flush=True)
            if _getch().lower() != 'y':
                print("\n")
                continue
            print()
            queue_file = os.path.join(parent_dir, 'speed_queue.txt')
            if not os.path.exists(queue_file):
                open(queue_file, 'a', encoding='utf-8').close()
            process_queue_file(queue_file)
            return

        if mode == 3:
            print("Proceed? (y/n): ", end='', flush=True)
            if _getch().lower() != 'y':
                print("\n")
                continue
            print()
            process_pending_deletes()
            return

        if mode not in (0, 1):
            continue

        Config.speed_factor = int(input("Choose speed (default:10): ") or 10)

        if mode == 1:
            playlist = get_video_paths_bulk()
            for video in playlist:
                args = construct_args([dict(name=video, start=None, end=None)])
                waitlist.append(args)
        elif mode == 0:
            videos = get_video_dicts_normal()
            if videos:
                args = construct_args(videos)
                waitlist.append(args)

        try:
            continue_ask = int(input("Construct waitlist for other videos? (0/1): "))
        except ValueError:
            print("Invalid input. Exiting.")
            break
        if not continue_ask:
            break

    for input_cmd, videos_dir, output_dir in waitlist:
        print(input_cmd)
        subprocess.run(input_cmd, shell=False, text=True, stderr=subprocess.STDOUT)

    for _, videos_dir, output_dir in waitlist:
        comp_result = compare_length(videos_dir, output_dir)
        subprocess.run([ffprob_fir, "-v", "error", "-i", output_dir])
        ask_delete(comp_result, videos_dir, output_dir)

if __name__ == "__main__":

    os_name = platform.system()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(script_dir, '..'))

    speedup_dir = os.path.join(parent_dir, 'speed up')

    if os_name == "Windows":
        ffmpeg_dir = os.path.join(parent_dir, 'ffmpeg/bin/ffmpeg.exe')
        ffprob_fir = os.path.join(parent_dir, 'ffmpeg/bin/ffprobe.exe')
    else:
        ffmpeg_dir = "/usr/bin/ffmpeg"
        ffprob_fir = "/usr/bin/ffprobe"

    main()



