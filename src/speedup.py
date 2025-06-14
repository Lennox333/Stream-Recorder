import subprocess
from pathlib import Path
import os
import send2trash as st
import re
from datetime import datetime
import asyncio


import platform


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

def compare_length(videos, output) -> bool:
    total = 0
    time_format = "%H\\:%M\\:%S"
    
    # Convert strings to datetime objects
    
    print(f"Comparing {output} / {[ video['name'] for video in videos]}")
    for video in videos:
        video_name = video['name']
        video_length = get_length(video_name)    

        start_time = video.get('start', None)
        end_time = video.get('end', None)
        if start_time and end_time:
            # If both start and end times are provided, calculate the duration between them
            start = datetime.strptime(start_time, time_format)
            end = datetime.strptime(end_time, time_format)
            total += (end - start).total_seconds()

        elif start_time:
            # If only start time is provided, calculate length from start to the end of the video
            start = datetime.strptime(start_time, time_format)
            total += video_length - (start - datetime(1900, 1, 1)).total_seconds()  # Calculate length from start to end of video
        elif end_time:
            # If only end time is provided, calculate length from the start of the video to end time
            end = datetime.strptime(end_time, time_format)
            total += (end - datetime(1900, 1, 1)).total_seconds()  # Calculate length from start to end time
        else:
            # If no start or end time is provided, add the whole video length
            total += video_length


    speed = get_length(output)
    
    if (abs(total - speed * 10) <= 120 ):    
        print(f"speed up ok! {speed}  {total}")
        return True
    
    print(f"somthimg is wrong, check again {speed}  {total}")
    return False

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

def build_trim_filter(index: int, start: str = '', end: str = '') -> str:
    if start and end:
        return f"[{index}:v]trim=start='{start}':end='{end}',setpts=PTS/10[v{index}]; "
    elif start:
        return f"[{index}:v]trim=start='{start}',setpts=PTS/10[v{index}]; "
    elif end:
        return f"[{index}:v]trim=end='{end}',setpts=PTS/10[v{index}]; "
    return f"[{index}:v]setpts=PTS/10[v{index}];"

    
def ask_delete(comp_result: bool, videos_dir: list):
    if comp_result:
        while True:
            y_n = input("Do u wanna delete original videos? (y/n): ")
            if y_n == 'y':
                delete_video(videos_dir)
                break
            elif 'n':
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

    matchStreamlinkFormat = re.search(r'\] (.*?)\.', output)
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
        try:
            mode = int(input("Choose mode: 0 - normal 1 - bulk: "))
        except ValueError:
            print("Invalid input. Please enter 0 or 1.")
            continue

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
        else:
            print("Invalid mode. Please enter 0 or 1.")
            continue

        try:
            continue_ask = int(input("Construct waitlist for other videos? (0/1): "))
        except ValueError:
            print("Invalid input. Exiting.")
            break
        if not continue_ask:
            break

    for input_cmd, videos_dir, output_dir in waitlist:
        print(input_cmd)
        subprocess.run(input_cmd, shell=False, text=True)

    for _, videos_dir, output_dir in waitlist:
        comp_result = compare_length(videos_dir, output_dir)
        subprocess.run([ffprob_fir, "-v", "error", "-i", output_dir])
        video_names = [video['name'] for video in videos_dir]
        ask_delete(comp_result, video_names)

if __name__ == "__main__": 

    os_name = platform.system()

    parent_dir = os.getcwd()

    speedup_dir = os.path.join( parent_dir, 'speed up')

    if os_name == "Windows":
        ffmpeg_dir = os.path.join(parent_dir, 'ffmpeg/bin/ffmpeg.exe')
        ffprob_fir = os.path.join(parent_dir, 'ffmpeg/bin/ffprobe.exe')
    else:
        ffmpeg_dir = "/usr/bin/ffmpeg"
        ffprob_fir = "/usr/bin/ffprobe"

    
    main()

