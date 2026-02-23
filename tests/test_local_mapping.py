import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from yoto_up.local_mapping import (
    _clean_title,
    load_local_mapping,
    save_local_mapping,
    add_mapping,
    get_mapping,
    auto_match_card,
)
from yoto_up.models import Card

@pytest.fixture
def mock_local_tracks_file(tmp_path):
    temp_file = tmp_path / "test_local_tracks.json"
    with patch("yoto_up.local_mapping.LOCAL_TRACKS_FILE", temp_file):
        yield temp_file

def test_clean_title():
    # Basic cases
    assert _clean_title("My Track") == "My Track"
    assert _clean_title("my track.mp3") == "My Track"
    assert _clean_title("Song Name.M4A") == "Song Name"
    # Track prefixes
    assert _clean_title("01 - First Song") == "First Song"
    assert _clean_title("12_Second_Song") == "Second Song"
    # Special characters
    assert _clean_title("Chapter (1)") == "Chapter 1"
    assert _clean_title("hello_world-test") == "Hello World Test"
    assert _clean_title("   Spaces   ") == "Spaces"

def test_load_save_mapping(mock_local_tracks_file):
    # Test load when file doesn't exist
    assert load_local_mapping() == {}

    # Test saving data
    test_data = {"yoto:#123": "/fake/path/audio.mp3"}
    save_local_mapping(test_data)

    # Test loading existing data
    loaded_data = load_local_mapping()
    assert loaded_data == test_data

@patch("yoto_up.local_mapping.load_local_mapping")
@patch("yoto_up.local_mapping.save_local_mapping")
def test_add_get_mapping(mock_save, mock_load):
    # Setup state
    internal_map = {}
    mock_load.return_value = internal_map
    def side_effect_save(data):
        internal_map.update(data)
    mock_save.side_effect = side_effect_save

    # Perform add
    add_mapping("http://example.com/audio.mp3", "/absolute/path.mp3")
    
    # Verify save occurred correctly
    assert internal_map == {"http://example.com/audio.mp3": "/absolute/path.mp3"}

    # Assert retrieved correctly
    assert get_mapping("http://example.com/audio.mp3") == "/absolute/path.mp3"
    assert get_mapping("missing_url") is None

@patch("yoto_up.local_mapping.Path.is_dir")
@patch("yoto_up.local_mapping.Path.rglob")
@patch("yoto_up.local_mapping._get_audio_duration")
@patch("yoto_up.local_mapping.save_local_mapping")
@patch("yoto_up.local_mapping.load_local_mapping")
def test_auto_match_card(mock_load_mapping, mock_save_mapping, mock_get_duration, mock_rglob, mock_isdir):
    test_card = Card(
        cardId="test_card_1",
        title="Test Story",
        content={
            "chapters": [
                {
                    "title": "Chapter One",
                    "tracks": [
                        {
                            "title": "Intro Track",
                            "duration": 120.5,
                            "trackUrl": "yoto:#track1",
                            "key": "k1",
                            "format": "mp3",
                            "type": "audio"
                        },
                        {
                            "title": "Main Story",
                            "duration": 600.0,
                            "trackUrl": "yoto:#track2",
                            "key": "k2",
                            "format": "mp3",
                            "type": "audio"
                        }
                    ]
                }
            ]
        }
    )

    mock_isdir.return_value = True

    # mock rglob to return specific files depending on extension
    def fake_rglob(pattern):
        if pattern == "*.mp3":
            return [Path("/mock/dir/01 Intro Track.mp3")]
        if pattern == "*.m4a":
            return [Path("/mock/dir/02 Main Story.m4a")]
        return []
    mock_rglob.side_effect = fake_rglob

    def fake_duration(path):
        pstr = str(path)
        if "Intro Track" in pstr:
            return 120.0
        if "Main Story" in pstr:
            return 601.5
        return 0
    mock_get_duration.side_effect = fake_duration

    mock_load_mapping.return_value = {}

    matched = auto_match_card(test_card, "/mock/dir")

    assert len(matched) == 2
    assert "yoto:#track1" in matched
    assert "01 Intro Track.mp3" in matched["yoto:#track1"]
    assert "yoto:#track2" in matched
    assert "02 Main Story.m4a" in matched["yoto:#track2"]
    
    mock_save_mapping.assert_called_once()
