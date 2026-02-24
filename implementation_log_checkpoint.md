# Implementation Checkpoint: Yoto API Metadata Refactor

## Current State
- **Uploads:** Audio uploads successfully transcode and link to the Yoto Card.
- **Playback:** The uploaded tracks are successfully playable on the Yoto API / App.
- **Titles:** Track titles are successfully parsing and appearing correctly on the Yoto web studio.
- **Missing Data (Bug):** The Yoto web studio still reports the track UI as having "no size and duration" despite being playable and having a title.

## Changes Made So Far
1. **Schema Tolerance:** Relaxed `pydantic` strictness on the `Track` model allowing `title` to be optional, preventing hard crashes when Yoto temporarily omits titles.
2. **Metadata Aggregation:** 
    - Discovered Yoto API sometimes returns track data split between `transcodedInfo` and `uploadInfo`.
    - Modified `get_track_from_transcoded_audio` and `get_chapter_from_transcoded_audio` to pull sizes and duration from both buckets as fallbacks.
    - Updated `upload_tasks.py` to correctly calculate and inject the top-level `CardMedia` attribute (duration/fileSize aggregate) which was completely missing before.

## Next Steps / Theories
The Yoto Web Studio is extremely explicit about the exact structure of the JSON payload. We suspect either:
1. `fileSize` or `duration` are incorrectly typed (e.g. they need to be integers instead of floats, or strings instead of numbers).
2. The Yoto Studio expects these fields to exist un-nested somewhere else in the `Track` schema that we haven't mapped yet.
3. The Yoto Studio expects `audio_path` native metadata to be present during the transcode instead of just passing the file. 

This log serves as a checkpoint before we continue diving into the precise JSON model mismatch.
