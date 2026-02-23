import json
import os
import re
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
from mutagen import File as MutagenFile

from yoto_up.paths import LOCAL_TRACKS_FILE, atomic_write

def load_local_mapping() -> Dict[str, str]:
    if not LOCAL_TRACKS_FILE.exists():
        return {}
    try:
        return json.loads(LOCAL_TRACKS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load local track mapping: {e}")
        return {}

def save_local_mapping(mapping: Dict[str, str]) -> None:
    try:
        data = json.dumps(mapping, ensure_ascii=False, indent=2)
        atomic_write(LOCAL_TRACKS_FILE, data, text_mode=True)
    except Exception as e:
        logger.error(f"Failed to save local track mapping: {e}")

def add_mapping(track_url: str, local_path: str) -> None:
    mapping = load_local_mapping()
    mapping[track_url] = str(Path(local_path).absolute())
    save_local_mapping(mapping)

def get_mapping(track_url: str) -> Optional[str]:
    mapping = load_local_mapping()
    return mapping.get(track_url)

def _clean_title(title: str) -> str:
    # remove leading numbers, punctuation, common extensions
    title = re.sub(r'^\s*\d{1,3}[\s\-\._:\)\]]+', '', title)
    title = re.sub(r'\.(mp3|m4a|wav|aac|flac|ogg)$', '', title, flags=re.IGNORECASE)
    # lowercase, replace non-alphanumeric with spaces
    title = re.sub(r'[^a-zA-Z0-9]', ' ', title).title()
    return re.sub(r'\s+', ' ', title).strip()

def _get_audio_duration(file_path: Path) -> Optional[float]:
    try:
        mf = MutagenFile(file_path)
        if mf is not None and hasattr(mf, 'info') and hasattr(mf.info, 'length'):
            return mf.info.length
    except Exception:
        pass
    return None

def auto_match_card(card, local_dir: str) -> Dict[str, str]:
    """
    Attempts to match tracks from a Card with audio files in a local directory.
    Returns a dictionary of new mappings added.
    """
    local_path = Path(local_dir)
    if not local_path.is_dir():
        return {}
        
    logger.info(f"Scanning {local_dir} for potential track matches...")
    audio_files = []
    # Using multiple extensions
    for ext in ('.mp3', '.m4a', '.wav', '.aac', '.flac', '.ogg'):
        from glob import glob
        # rglob handles recursive search
        audio_files.extend(list(local_path.rglob(f"*{ext}")))
    
    file_candidates = []
    import sys
    sys.stdout.write(f"Found {len(audio_files)} potential audio files.\n")
    for f in audio_files:
        dur = _get_audio_duration(f)
        if dur is not None:
            file_candidates.append({
                "path": f,
                "duration": dur,
                "clean_name": _clean_title(f.stem)
            })
            
    if not file_candidates:
        logger.warning(f"No audio files found or duration readable in {local_dir}")
        return {}
        
    mapping = load_local_mapping()
    new_matches = {}
    
    if not card or not card.content or not card.content.chapters:
        return {}
        
    for chapter in card.content.chapters:
        for track in getattr(chapter, 'tracks', []):
            if not track.trackUrl or not track.trackUrl.startswith("yoto:#"):
                continue
                
            if track.trackUrl in mapping:
                continue # Already tracked
                
            yoto_duration = getattr(track, 'duration', None)
            yoto_title = _clean_title(getattr(track, 'title', ''))
            
            best_match = None
            
            for candidate in file_candidates:
                # Require duration match within 1.5 seconds
                if yoto_duration and abs(candidate["duration"] - yoto_duration) <= 1.5:
                    # Plus some similarity in title to be safe, e.g. one string is in the other
                    if len(yoto_title) > 2 and (yoto_title in candidate["clean_name"] or candidate["clean_name"] in yoto_title):
                        best_match = candidate["path"]
                        break
                        
            if best_match:
                mapping[track.trackUrl] = str(best_match.absolute())
                new_matches[track.trackUrl] = str(best_match.absolute())
                logger.info(f"Matched {track.title} -> {best_match}")
                
    if new_matches:
        save_local_mapping(mapping)
        
    return new_matches
