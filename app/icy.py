import logging
import re
import httpx

logger = logging.getLogger("app.icy")


def parse_icy_payload(payload: str) -> dict | None:
    """
    Parses a raw ICY payload string like StreamTitle='Artist - Song';StreamUrl='http...';
    """
    if not payload or "StreamTitle=" not in payload:
        return None

    title_match = re.search(r"StreamTitle='(.*?)';", payload)
    if not title_match:
        return None

    raw_title = title_match.group(1).strip()
    if not raw_title or raw_title in ("kz", "CDN", "Live Stream"):
        return None

    # Separate Artist and Song Title if delimited by " - "
    if " - " in raw_title:
        parts = raw_title.split(" - ", 1)
        artist = parts[0].strip()
        song_title = parts[1].strip()
    else:
        artist = ""
        song_title = raw_title

    # Extract optional StreamUrl for artwork
    cover_url = None
    url_match = re.search(r"StreamUrl='(.*?)';", payload)
    if url_match:
        extracted_url = url_match.group(1).strip()
        if extracted_url.startswith("http://") or extracted_url.startswith("https://"):
            cover_url = extracted_url

    return {
        "artist": artist,
        "title": song_title,
        "has_track_info": True,
        "cover_url": cover_url,
    }


async def fetch_icy_metadata(stream_url: str, timeout: float = 3.0) -> dict | None:
    """
    Probes an audio stream URL with Icy-MetaData header and extracts
    the live StreamTitle and optional StreamUrl artwork.
    """
    if not stream_url or not stream_url.startswith("http"):
        return None

    headers = {
        "Icy-MetaData": "1",
        "User-Agent": "VLC/3.0.18 LibVLC/3.0.18",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", stream_url, headers=headers) as response:
                metaint_str = response.headers.get("icy-metaint")
                if not metaint_str:
                    return None

                try:
                    metaint = int(metaint_str)
                except ValueError:
                    return None

                buffer = bytearray()
                max_read = metaint + 4096

                async for chunk in response.aiter_bytes():
                    buffer.extend(chunk)
                    if len(buffer) >= metaint + 1:
                        meta_len_byte = buffer[metaint]
                        meta_len = meta_len_byte * 16
                        if meta_len > 0 and len(buffer) >= metaint + 1 + meta_len:
                            raw_bytes = buffer[metaint + 1 : metaint + 1 + meta_len]
                            raw_str = raw_bytes.decode("utf-8", errors="ignore").rstrip("\x00")
                            return parse_icy_payload(raw_str)
                        elif meta_len == 0:
                            return None
                    if len(buffer) > max_read:
                        break
    except Exception as exc:
        logger.debug(f"ICY probe failed for {stream_url}: {exc}")

    return None
