"""
Encoding and compatibility profile presets registry.
"""

from typing import Dict, List, Optional
from app.core.constants import OutputContainer, QualityPreset
from app.models.preset import BUILTIN_PRESETS, TranscodePreset


class ProfileManager:
    """Provides lookup and construction of transcode presets."""

    @staticmethod
    def get_all_presets() -> List[TranscodePreset]:
        return list(BUILTIN_PRESETS)

    @staticmethod
    def get_preset_by_id(preset_id: str) -> Optional[TranscodePreset]:
        if preset_id == "tv_lcd_compatible":
            preset_id = "universal_mp4"
        for p in BUILTIN_PRESETS:
            if p.id == preset_id:
                return p
        return BUILTIN_PRESETS[0] if BUILTIN_PRESETS else None

    @staticmethod
    def get_preset_for_quality(quality_preset: QualityPreset) -> TranscodePreset:
        if quality_preset in (QualityPreset.UNIVERSAL_MP4, QualityPreset.TV_LCD_COMPATIBLE):
            return ProfileManager.get_preset_by_id("universal_mp4")
        elif quality_preset == QualityPreset.MAXIMUM_COMPATIBILITY:
            return ProfileManager.get_preset_by_id("maximum_compatibility")
        elif quality_preset == QualityPreset.BALANCED:
            return ProfileManager.get_preset_by_id("balanced_mp4")
        elif quality_preset == QualityPreset.BEST_QUALITY:
            return ProfileManager.get_preset_by_id("original_best_quality")
        elif quality_preset == QualityPreset.AUDIO_ONLY:
            return ProfileManager.get_preset_by_id("audio_mp3_320k")
        return ProfileManager.get_preset_by_id("universal_mp4")
