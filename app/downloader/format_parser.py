"""
Parser and categorizer for raw yt-dlp format trees.
"""

from typing import List, Optional
from app.models.format_info import FormatItem


class FormatParser:
    """Parses raw yt-dlp format dictionaries into clean, typed FormatItem objects."""

    @staticmethod
    def parse_formats(raw_formats: list[dict], duration: Optional[float] = None) -> List[FormatItem]:
        if not raw_formats:
            return []

        parsed_items: List[FormatItem] = []

        for f in raw_formats:
            fmt_id = str(f.get("format_id", ""))
            ext = f.get("ext", "mp4")
            vcodec = f.get("vcodec", "none") or "none"
            acodec = f.get("acodec", "none") or "none"

            has_video = vcodec.lower() != "none"
            has_audio = acodec.lower() != "none"

            if not has_video and not has_audio:
                continue

            is_combined = has_video and has_audio

            width = f.get("width")
            height = f.get("height")
            fps = f.get("fps")

            # Resolution string
            resolution = "Audio Only"
            if height:
                resolution = f"{height}p"
                if height >= 2160:
                    resolution = f"{height}p (4K)"
                elif height >= 1440:
                    resolution = f"{height}p (2K)"
                elif height >= 1080:
                    resolution = f"{height}p (FHD)"
                elif height >= 720:
                    resolution = f"{height}p (HD)"
            elif f.get("resolution"):
                resolution = str(f.get("resolution"))

            # Dynamic Range
            dyn_range = f.get("dynamic_range")

            # Bitrates
            abr = f.get("abr")
            vbr = f.get("vbr")
            tbr = f.get("tbr")

            # File size calculation
            filesize = f.get("filesize")
            filesize_approx = f.get("filesize_approx")
            if not filesize and not filesize_approx and tbr and duration and duration > 0:
                # Estimate: tbr in kbit/s -> bytes = (tbr * 1000 / 8) * duration
                filesize_approx = int((tbr * 1000 / 8) * duration)

            parsed_items.append(FormatItem(
                format_id=fmt_id,
                ext=ext,
                resolution=resolution,
                width=int(width) if width else None,
                height=int(height) if height else None,
                fps=float(fps) if fps else None,
                vcodec=vcodec,
                acodec=acodec,
                abr=float(abr) if abr else None,
                vbr=float(vbr) if vbr else None,
                tbr=float(tbr) if tbr else None,
                filesize=int(filesize) if filesize else None,
                filesize_approx=int(filesize_approx) if filesize_approx else None,
                format_note=f.get("format_note", "") or "",
                dynamic_range=dyn_range,
                has_video=has_video,
                has_audio=has_audio,
                is_combined=is_combined,
                protocol=f.get("protocol", ""),
                container=f.get("container", ext),
                aspect_ratio=f.get("aspect_ratio")
            ))

        # Sort: Combined > Video Only > Audio Only, then by Height (descending), then TBR (descending)
        def sort_key(item: FormatItem):
            type_weight = 3 if item.is_combined else (2 if item.has_video else 1)
            h = item.height or 0
            br = item.tbr or item.vbr or item.abr or 0
            return (type_weight, h, br)

        parsed_items.sort(key=sort_key, reverse=True)
        return parsed_items
