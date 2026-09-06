from app.encoder.profiles import ProfileManager
from app.models.job import ConvertJob
from app.models.preset import TranscodePreset


def test_audio_mp3_presets_exist():
    presets = ProfileManager.get_all_presets()
    preset_ids = [p.id for p in presets]
    
    assert "audio_mp3_320k" in preset_ids
    assert "audio_mp3_256k" in preset_ids
    assert "audio_mp3_192k" in preset_ids
    assert "audio_mp3_128k" in preset_ids
    assert "audio_wav" in preset_ids
    assert "audio_flac" in preset_ids
    assert "universal_mp4" in preset_ids


def test_profile_manager_lookup():
    p320 = ProfileManager.get_preset_by_id("audio_mp3_320k")
    assert p320 is not None
    assert p320.audio_codec == "libmp3lame"
    assert p320.audio_bitrate == "320k"
    assert p320.container == "mp3"
    assert p320.is_audio_only is True

    # Check universal_mp4
    univ = ProfileManager.get_preset_by_id("universal_mp4")
    assert univ is not None
    assert univ.video_codec == "libx264"
    assert univ.audio_codec == "aac"
    assert univ.pixel_format == "yuv420p"


def test_convert_job_with_trimming():
    job = ConvertJob(
        input_file_path="input.mp4",
        output_file_path="output.mp3",
        preset_id="audio_mp3_320k",
        trim_enabled=True,
        trim_start="00:00:10",
        trim_end="00:01:45",
        audio_bitrate="320k"
    )
    
    assert job.trim_enabled is True
    assert job.trim_start == "00:00:10"
    assert job.trim_end == "00:01:45"
    assert job.audio_bitrate == "320k"
    assert job.source_path == "input.mp4"
    assert job.output_path == "output.mp3"

