## Local Livestream Packs

Put each approved livestream in its own folder under `assets/livestream/library/`.

Example:

```text
assets/
  livestream/
    current.txt
    library/
      forest-pool-river-calm/
        video.mp4
        audio.mp3
        manifest.json
```

Rules:

- `current.txt` should contain the folder name of the pack you want to use next
- each pack needs one supported video file and one supported audio file
- `manifest.json` is optional but recommended
- if `current.txt` is missing or empty, the newest valid pack is used
- generated packs created by `python main.py --generate-pack` land alongside manual packs under `library/`

Supported manifest fields:

- `title`
- `description`
- `thumbnail_title`
- `thumbnail_subtitle`
- `badge_text`
- `tags`
