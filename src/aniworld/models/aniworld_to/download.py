"""Combine AniWorld's German-subbed video and German-dubbed audio."""

import platform
from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory

import ffmpeg

from ...config import PROVIDER_HEADERS_D, get_video_codec, logger
from ..common import common
from ..common.numbering import EPISODE_URL_PREFIX


def _download_track(episode, language, target, label):
    source = copy(episode)
    source.selected_language = language
    providers = source.provider_attempt_order()
    if not providers:
        raise ValueError(f"No provider available for {language}")

    errors = {}
    for provider in providers:
        if not source.provider_link(language, provider):
            errors[provider] = f"{language} is unavailable"
            continue
        headers = PROVIDER_HEADERS_D.get(provider, {})
        for attempt in range(1, 4):
            source.selected_provider = provider
            try:
                stream_url = source.stream_url
                if language == "German Dub":
                    common._download_audio_track(
                        stream_url, provider, headers, target, "deu", label
                    )
                else:
                    common._download_full_stream(
                        stream_url,
                        target,
                        common._download_input_kwargs(stream_url, headers),
                        headers,
                        {},
                        get_video_codec(),
                        label,
                        None,
                        video_only=True,
                    )
                return
            except common.DownloadCancelled:
                raise
            except Exception as exc:
                errors[provider] = str(exc)
                target.unlink(missing_ok=True)
                logger.warning(
                    f"{language} via {provider} failed (attempt {attempt}/3): {exc}"
                )

    raise RuntimeError(common._build_provider_failure_message(language, errors))


def _existing_tracks(path):
    if path.is_file():
        try:
            return ffmpeg.probe(path).get("streams", [])
        except ffmpeg.Error:
            pass
    return []


def _warn_if_track_lengths_differ(path):
    tracks = _existing_tracks(path)[:2]
    lengths = [
        common._parse_ffmpeg_time(track.get("tags", {}).get("DURATION", ""))
        for track in tracks
    ]
    if len(lengths) == 2 and all(lengths) and abs(lengths[0] - lengths[1]) > 2:
        logger.warning(
            f"German Sub video and German Dub audio differ in length by "
            f"{abs(lengths[0] - lengths[1]):.1f} seconds. Check playback sync."
        )


def download_german_sub_dub(episode):
    """Reuse matching local tracks and publish the finished file atomically."""
    if platform.system() == "Windows":
        common.DependencyManager().fetch_binary("ffmpeg")

    common._prepare_resolution_naming(episode)
    target = episode._episode_path
    tracks = _existing_tracks(target)
    german = {}
    for track in tracks:
        if track.get("tags", {}).get("language") == "deu" and not track.get(
            "disposition", {}
        ).get("attached_pic"):
            german.setdefault(track["codec_type"], track)
    if all(
        german.get(kind, {}).get("disposition", {}).get("default")
        for kind in ("video", "audio")
    ):
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    label = common._progress_file_name(episode)
    existing = ffmpeg.input(str(target))
    with TemporaryDirectory(prefix=".aniworld-mux-", dir=target.parent) as tmp:
        staged = Path(tmp)
        inputs = []
        used = set()
        for kind, language in (("video", "German Sub"), ("audio", "German Dub")):
            if kind in german:
                index = german[kind]["index"]
                inputs.append(existing[str(index)])
                used.add(index)
            else:
                track_path = staged / f"{target.stem}.temp_{kind}.mkv"
                _download_track(episode, language, track_path, f"{label} ({language})")
                inputs.append(ffmpeg.input(str(track_path))["0"])
        inputs.extend(
            existing[str(track["index"])]
            for track in tracks
            if track["index"] not in used
        )

        mux = staged / f"{target.stem}.new.mkv"
        common._run_ffmpeg_with_progress(
            ffmpeg.output(
                *inputs,
                str(mux),
                c="copy",
                metadata=f"comment={EPISODE_URL_PREFIX}{episode.url}",
                **{
                    "metadata:s:0": "language=deu",
                    "metadata:s:1": "language=deu",
                    "metadata:s:v:0": "title=German Sub",
                    "metadata:s:a:0": "title=German Dub",
                    "disposition:v": "-default",
                    "disposition:a": "-default",
                    "disposition:v:0": "+default",
                    "disposition:a:0": "+default",
                },
            ),
            label=label,
        )
        _warn_if_track_lengths_differ(mux)
        # Convert inside the staging directory so a failed MP4 conversion also
        # leaves the existing file intact and cleans up its partial output.
        if target.suffix.lower() == ".mp4":
            converted = staged / f"{target.stem}.new.mp4"
            common._finalize_episode(mux, converted, label)
            mux = converted
        common._finalize_episode(mux, target, label, owner=episode)
