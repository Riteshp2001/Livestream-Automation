import os
import shutil
import subprocess


def get_ffmpeg_binary():
    ffmpeg_binary = shutil.which("ffmpeg")
    if ffmpeg_binary:
        return ffmpeg_binary

    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        return get_ffmpeg_exe()
    except Exception as error:
        raise RuntimeError("ffmpeg is not installed or not available on PATH.") from error


def _run_ffmpeg_process(cmd, duration_seconds):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _, stderr = process.communicate(timeout=duration_seconds + 120)
        if process.returncode != 0:
            print(f"ffmpeg exited with code {process.returncode}")
            print(f"stderr: {stderr.decode('utf-8', errors='replace')[-2000:]}")
        else:
            print("ffmpeg job completed successfully.")
    except subprocess.TimeoutExpired:
        print("ffmpeg job duration exceeded, terminating...")
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        print("ffmpeg job terminated.")

    return process.returncode


def _stream_output_args(rtmp_url, stream_key, local_recording_path=None):
    rtmp_endpoint = f"{rtmp_url}/{stream_key}"
    if not local_recording_path:
        return ["-f", "flv", rtmp_endpoint]

    os.makedirs(os.path.dirname(local_recording_path), exist_ok=True)
    archive_target = local_recording_path.replace("\\", "/")
    return [
        "-flags",
        "+global_header",
        "-f",
        "tee",
        f"[f=flv:onfail=ignore]{rtmp_endpoint}|[f=mp4:movflags=+faststart:onfail=ignore]{archive_target}",
    ]


def start_rtmp_stream(video_file, audio_file, rtmp_url, stream_key, duration_seconds, local_recording_path=None):
    ffmpeg_binary = get_ffmpeg_binary()
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-stream_loop",
        "-1",
        "-re",
        "-i",
        video_file,
        "-stream_loop",
        "-1",
        "-i",
        audio_file,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        "4500k",
        "-maxrate",
        "4500k",
        "-bufsize",
        "9000k",
        "-pix_fmt",
        "yuv420p",
        "-g",
        "60",
        "-keyint_min",
        "60",
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-t",
        str(duration_seconds),
    ]
    cmd.extend(_stream_output_args(rtmp_url, stream_key, local_recording_path))

    print("Starting RTMP stream to YouTube...")
    print(f"  Duration: {duration_seconds // 60} minutes")
    print("  Resolution: 1920x1080")
    print("  Video bitrate: 4500k")
    if local_recording_path:
        print(f"  Local archive: {local_recording_path}")
    return _run_ffmpeg_process(cmd, duration_seconds)


def start_browser_capture_stream(
    display,
    audio_file,
    rtmp_url,
    stream_key,
    duration_seconds,
    local_recording_path=None,
    width=1920,
    height=1080,
    audio_is_playlist=False,
):
    ffmpeg_binary = get_ffmpeg_binary()
    display_input = display if "+" in display else f"{display}.0+0,0"
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        "30",
        "-f",
        "x11grab",
        "-i",
        display_input,
    ]

    # Audio input — static looped file OR dynamic concat playlist
    if audio_is_playlist:
        cmd.extend([
            "-f",    "concat",
            "-safe", "0",
            "-re",
            "-i",    audio_file,
        ])
    else:
        cmd.extend([
            "-stream_loop", "-1",
            "-i",           audio_file,
        ])

    cmd.extend([
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v",        "libx264",
        "-preset",     "veryfast",
        "-b:v",        "4500k",
        "-maxrate",    "4500k",
        "-bufsize",    "9000k",
        "-pix_fmt",    "yuv420p",
        "-g",          "60",
        "-keyint_min", "60",
        "-sc_threshold", "0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar",  "44100",
        "-t",   str(duration_seconds),
    ])
    cmd.extend(_stream_output_args(rtmp_url, stream_key, local_recording_path))

    print("Starting live browser capture RTMP stream...")
    print(f"  Display input:  {display_input}")
    print(f"  Audio source:   {'playlist (switchable)' if audio_is_playlist else 'static loop'}")
    print(f"  Audio file:     {audio_file}")
    if local_recording_path:
        print(f"  Local archive:  {local_recording_path}")
    return _run_ffmpeg_process(cmd, duration_seconds)


def transcode_video(input_file, output_file, fps=30, timeout_seconds=300):
    ffmpeg_binary = get_ffmpeg_binary()
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        input_file,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        output_file,
    ]
    return _run_ffmpeg_process(cmd, timeout_seconds)
