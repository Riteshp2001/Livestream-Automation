# Generated Stream Sounds

This folder is reserved for repo-owned generated audio assets that should plug into the same
`stream_sound_catalog` flow as the base ambient library.

Structure:

- `catalogs/` contains generator-specific catalog JSON files merged at runtime
- `supriya/` contains rendered audio files created from in-repo Supriya presets

The generated catalogs are optional. If no generator has produced assets yet, the livestream
runtime continues to use the base `stream_sound_catalog.json` only.
