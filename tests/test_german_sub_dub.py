"""Verify the download preset, audio selection, and safe retries."""

import shutil
import subprocess
from types import SimpleNamespace

import ffmpeg
import pytest

from aniworld.config import GERMAN_SUB_DUB
from aniworld.models import AniworldEpisode
from aniworld.models.aniworld_to import download
from aniworld.models.common import common, hls

MASTER = "https://media.example/episode/master.m3u8?t=a%2Fb&v=1"
AUDIO = "https://media.example/episode/index-f1-a1.m3u8?token=audio"


@pytest.mark.parametrize("codec", ["mp4a.40.2", "avc1.640028,mp4a.40.2"])
@pytest.mark.parametrize("provider", ["VOE", "Filemoon"])
def test_track_selector_requires_an_audio_only_manifest(monkeypatch, codec, provider):
    def fetch(url, headers):
        assert url == MASTER.replace("master.m3u8", "master-a1.m3u8")
        assert headers["Referer"] == "https://example.org"
        return (
            "#EXTM3U\n"
            f'#EXT-X-STREAM-INF:BANDWIDTH=64000,CODECS="{codec}"\n'
            "index-f2-a1.m3u8?token=other\n"
            f'#EXT-X-STREAM-INF:BANDWIDTH=256000,CODECS="{codec}"\n'
            "index-f1-a1.m3u8?token=audio\n"
        )

    monkeypatch.setattr(hls, "_fetch_text", fetch)
    assert hls.find_audio_only_playlist(
        MASTER, provider, {"Referer": "https://example.org"}
    ) == (AUDIO if codec == "mp4a.40.2" else None)


@pytest.mark.parametrize("cancel", [False, True])
def test_failed_audio_playlist_falls_back_but_cancellation_does_not(
    tmp_path, monkeypatch, cancel
):
    monkeypatch.setattr(hls, "find_audio_only_playlist", lambda *_: AUDIO)
    monkeypatch.setenv("ANIWORLD_HLS_CONCURRENCY", "1")
    target = tmp_path / "dub.mkv"
    sources = []

    def run(node, label):
        args = ffmpeg.compile(node)
        src = args[args.index("-i") + 1]
        sources.append(src)
        if src == AUDIO:
            target.write_bytes(b"partial")
            if cancel:
                raise common.DownloadCancelled
            raise RuntimeError("audio playlist unavailable")
        assert not target.exists()
        target.write_bytes(b"completed")

    monkeypatch.setattr(common, "_run_ffmpeg_with_progress", run)
    if cancel:
        with pytest.raises(common.DownloadCancelled):
            common._download_audio_track(MASTER, "VOE", {}, target, "deu", "Episode")
        assert sources == [AUDIO]
    else:
        common._download_audio_track(MASTER, "VOE", {}, target, "deu", "Episode")
        assert sources == [AUDIO, MASTER]
        assert target.read_bytes() == b"completed"


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="requires local FFmpeg tools",
)
@pytest.mark.parametrize("existing_sub", [False, True])
def test_download_combines_tracks_and_retry_reuses_them(
    tmp_path, monkeypatch, existing_sub
):
    monkeypatch.setattr(
        common.DependencyManager, "fetch_binary", lambda self, name: name
    )
    monkeypatch.setenv("ANIWORLD_NAMING_TEMPLATE", "{title}.{language}.mkv")
    episode = AniworldEpisode(
        "https://aniworld.to/anime/stream/example/staffel-1/episode-1",
        series=SimpleNamespace(
            title_cleaned="Example", release_year="2024", imdb="tt123"
        ),
        season=SimpleNamespace(season_number=1),
        episode_number=1,
        title_en="Example",
        selected_path=tmp_path,
        selected_language=GERMAN_SUB_DUB,
    )
    target = episode._episode_path

    def make_media(path, inputs, options):
        subprocess.run(
            ["ffmpeg", "-v", "error", *inputs, "-t", "1", *options, str(path)],
            check=True,
            capture_output=True,
        )

    video_input = ["-f", "lavfi", "-i", "color=blue:size=32x32:rate=10"]
    dub_input = ["-f", "lavfi", "-i", "sine=frequency=880"]
    if existing_sub:
        make_media(
            target,
            video_input + ["-f", "lavfi", "-i", "sine=frequency=440"],
            [
                "-c:v",
                "mpeg4",
                "-c:a",
                "aac",
                "-metadata:s:v:0",
                "language=deu",
                "-metadata:s:a:0",
                "language=jpn",
            ],
        )
    requested = []
    fail_dub = True

    def fetch(_episode, language, path, _label):
        requested.append(language)
        if language == "German Sub":
            make_media(path, video_input, ["-c:v", "mpeg4"])
        elif fail_dub:
            raise RuntimeError("dub unavailable")
        else:
            make_media(path, dub_input, ["-c:a", "aac"])

    monkeypatch.setattr(download, "_download_track", fetch)
    original = target.read_bytes() if existing_sub else None
    with pytest.raises(RuntimeError, match="dub unavailable"):
        episode.download()
    assert (target.read_bytes() if target.exists() else None) == original
    assert not list(tmp_path.glob(".aniworld-mux-*"))

    fail_dub = False
    requested.clear()
    episode.download()
    assert requested == (
        ["German Dub"] if existing_sub else ["German Sub", "German Dub"]
    )
    tracks = ffmpeg.probe(target)["streams"]
    assert [
        (s["codec_type"], s["tags"]["language"], s["tags"]["title"]) for s in tracks[:2]
    ] == [("video", "deu", "German Sub"), ("audio", "deu", "German Dub")]
    assert all(s["disposition"]["default"] for s in tracks[:2])
    assert len(tracks) == (3 if existing_sub else 2)
    if existing_sub:
        assert tracks[2]["tags"]["language"] == "jpn"
        assert not tracks[2]["disposition"]["default"]
    requested.clear()
    episode.download()
    assert not requested
