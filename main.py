import json
import sys

from lib.audio_generation.entrypoints import (
    run_audio_generator_status_mode,
    run_generate_supriya_sounds_mode,
)
from lib.livestream_entrypoints import (
    run_generate_example_sets_mode,
    run_generate_pack_mode,
    run_generate_profile_reviews_mode,
    run_generate_test_videos_mode,
    run_livestream_mode,
    run_resolve_stream_profile_mode,
)

sys.dont_write_bytecode = True


def run_groq_symphony_mode():
    """
    Fully autonomous Groq-directed Symphony Music Video generation.

    Groq decides EVERYTHING:
      • Which stream profile (sound environment) is most soothing right now
      • Which visualizer renders it
      • Which color palette to use
      • Which daypart / season atmosphere to evoke

    The result is a generated stream pack ready to play or upload.
    Set USE_GROQ_SYMPHONY_DIRECTOR=1 in .env (already done) and run:
        python main.py --groq-symphony
    """
    import os
    from lib.generated_stream_runtime import create_generated_pack
    from lib.livestream_entrypoints import (
        append_stream_history,
        _visual_loop_seconds,
        _stream_duration_minutes,
    )

    # Force the director on for this mode regardless of env
    os.environ["USE_GROQ_SYMPHONY_DIRECTOR"] = "1"

    print("\n" + "═" * 64)
    print("  🎼  GROQ AUTONOMOUS SYMPHONY DIRECTOR  🎼")
    print("  Groq will decide the most soothing symphony right now.")
    print("═" * 64 + "\n")

    duration_seconds  = _visual_loop_seconds()
    display_duration  = int(_stream_duration_minutes(20) * 60)
    render_mode       = os.getenv("STREAM_RENDER_MODE", "prerender")

    generated = create_generated_pack(
        duration_seconds=duration_seconds,
        display_duration_seconds=display_duration,
        render_mode=render_mode,
        # All profile/visualizer decisions delegated to Groq — pass no overrides
    )

    plan     = generated["plan"]
    metadata = generated["metadata"]
    decision = plan.get("groq_symphony_decision") or {}

    print("\n" + "─" * 64)
    print(f"  ✅  Symphony Pack Generated!")
    print(f"  📂  Output: {generated['output_dir']}")
    print(f"  🎵  Profile  : {plan['profile_id']}")
    print(f"  🌊  Visualizer: {plan['visualizer_id']}")
    print(f"  🌙  Daypart  : {plan['daypart']} / {plan['season']}")
    if decision.get("soothing_reasoning"):
        print(f"  💭  Groq says: \"{decision['soothing_reasoning']}\"")
    print(f"  🎬  Title    : {metadata.get('title', '—')}")
    print("─" * 64 + "\n")

    append_stream_history({
        "theme"          : plan["profile"]["display_name"],
        "render_mode"    : render_mode,
        "profile_id"     : plan["profile_id"],
        "seed"           : plan["seed"],
        "visualizer_id"  : plan["visualizer_id"],
        "title"          : metadata.get("title", ""),
        "groq_director"  : decision,
        "generated_pack_dir": generated["output_dir"],
    })


def run_auto_mode():
    from lib.content_handler import (
        load_used_content,
        save_used_content,
        search_and_download_meditation_video,
        search_and_download_music,
    )
    from lib.metadata import generate_metadata
    from lib.video_processing import combine_audio_video
    from lib.youtube_upload import refresh_token, upload_to_youtube

    used_content = load_used_content()

    with open("auto.json", "r", encoding="utf-8") as handle:
        config = json.load(handle)

    video_created = False

    while config["videos"] and not video_created:
        video_config = config["videos"].pop(0)
        video_query = video_config["video_query"]
        audio_query = video_config["audio_query"]
        should_upload_to_youtube = video_config["upload_to_youtube"]
        video_type = video_config["video_type"]
        duration_minutes = video_config["duration_minutes"]

        is_short = video_type == "short"

        video_url = search_and_download_meditation_video(used_content["videos"], video_query)
        if not video_url:
            print(f"Retrying with next config: Could not find a video for '{video_query}'")
            continue

        used_content["videos"].append(video_url)

        audio_url, attribution_text = search_and_download_music(audio_query, used_content["audios"])
        if not audio_url:
            print(f"Retrying with next config: Could not find audio for '{audio_query}'")
            continue

        used_content["audios"].append(audio_url)
        save_used_content(used_content)

        metadata = generate_metadata(video_query, duration_minutes, attribution=attribution_text, is_short=is_short)
        combine_audio_video("video.mp4", "music.mp3", "final_video.mp4", duration_minutes=duration_minutes, is_short=is_short)

        if should_upload_to_youtube:
            refresh_token()
            upload_to_youtube("final_video.mp4", metadata, is_short=is_short)

        with open("auto.json", "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=4)

        print(f"Successfully processed and uploaded video for query: '{video_query}'")
        video_created = True

    if not video_created:
        print("All video configurations have been processed or none were successful.")


def run_interactive_mode():
    from lib.content_handler import (
        load_used_content,
        save_used_content,
        search_and_download_meditation_video,
        search_and_download_music,
    )
    from lib.metadata import generate_metadata
    from lib.video_processing import combine_audio_video
    from lib.youtube_upload import refresh_token, upload_to_youtube

    used_content = load_used_content()

    while True:
        video_type = input("Do you want to create a Short or a regular video? (Enter 'short' or 'video'): ")
        duration_minutes = float(input("Enter the duration for the video (in minutes): "))
        video_query = input("Enter the search query for the Pixabay video: ")
        audio_query = input("Enter the search query for the Freesound music: ")
        is_short = video_type == "short"

        video_url = search_and_download_meditation_video(used_content["videos"], video_query)
        if video_url:
            used_content["videos"].append(video_url)

        audio_url, attribution_text = search_and_download_music(audio_query, used_content["audios"])
        if audio_url:
            used_content["audios"].append(audio_url)

        while True:
            user_input = input(
                "\nReview the downloaded video and music. Please select an option. "
                "\n1) Proceed to making the final video "
                "\n2) Download a new video "
                "\n3) Download new music "
                "\n4) Download a new video and music\n"
            ).lower()

            if user_input == "1":
                break
            if user_input == "2":
                video_url = search_and_download_meditation_video(used_content["videos"])
                if video_url:
                    used_content["videos"].append(video_url)
                continue
            if user_input == "3":
                audio_url, attribution_text = search_and_download_music("rain thunder", used_content["audios"])
                if audio_url:
                    used_content["audios"].append(audio_url)
                continue
            if user_input == "4":
                video_url = search_and_download_meditation_video(used_content["videos"])
                if video_url:
                    used_content["videos"].append(video_url)
                audio_url, attribution_text = search_and_download_music("rain thunder", used_content["audios"])
                if audio_url:
                    used_content["audios"].append(audio_url)

        save_used_content(used_content)

        metadata = generate_metadata(video_query, duration_minutes, attribution=attribution_text, is_short=is_short)
        combine_audio_video("video.mp4", "music.mp3", "final_video.mp4", duration_minutes=duration_minutes, is_short=is_short)

        upload_choice = input("Do you want to upload the video to YouTube? (yes/no): ").lower()
        if upload_choice == "yes":
            refresh_token()
            upload_to_youtube("final_video.mp4", metadata, is_short=is_short)

        repeat = input("Do you want to create another video? (yes/no): ").lower()
        if repeat != "yes":
            break


def main():
    from lib.livestream import LivestreamSetupError

    try:
        if "--livestream" in sys.argv:
            run_livestream_mode()
        elif "--generate-pack" in sys.argv:
            run_generate_pack_mode()
        elif "--generate-example-sets" in sys.argv:
            run_generate_example_sets_mode()
        elif "--generate-test-videos" in sys.argv:
            run_generate_test_videos_mode()
        elif "--generate-profile-reviews" in sys.argv:
            run_generate_profile_reviews_mode()
        elif "--resolve-stream-profile" in sys.argv:
            run_resolve_stream_profile_mode()
        elif "--audio-generator-status" in sys.argv:
            run_audio_generator_status_mode()
        elif "--generate-supriya-sounds" in sys.argv:
            run_generate_supriya_sounds_mode()
        elif "--auto" in sys.argv:
            run_auto_mode()
        elif "--groq-symphony" in sys.argv:
            run_groq_symphony_mode()
        else:
            run_interactive_mode()
    except LivestreamSetupError as error:
        print(f"FATAL: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
