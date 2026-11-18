# AniWorld Downloader – eierman324's fork

This is a fork of [AniWorld Downloader](https://github.com/phoenixthrush/AniWorld-Downloader) by phoenixthrush. It holds additions that aren't (yet) part of the original. Each one lives on its own branch, based on the original and kept in sync with it.

This page is only an overview: pick a feature below to open its branch, with the code and its README.

## Features

| Feature | What it does | Branch |
| --- | --- | --- |
| **Mediathek** | Search and download from the media libraries of the German, Austrian and Swiss public broadcasters (ARD, ZDF, Arte, 3sat, KiKA, ORF, SRF and more, 30 channels) through MediathekView, straight from the broadcasters. Seasons, language versions, quality and subtitles included. | [![Open the Mediathek branch](https://img.shields.io/badge/open-feature%2Fmediathekview-2ea44f?style=for-the-badge&logo=github)](https://github.com/eierman324/AniWorld-Downloader/tree/feature/mediathekview) |

The original, unchanged:

[![Open the upstream mirror](https://img.shields.io/badge/open-models%20%28upstream%29-555555?style=for-the-badge&logo=github)](https://github.com/eierman324/AniWorld-Downloader/tree/models)

## Install

[![Latest release](https://img.shields.io/github/v/release/eierman324/AniWorld-Downloader?style=for-the-badge&label=release)](https://github.com/eierman324/AniWorld-Downloader/releases/latest)

The [latest release](https://github.com/eierman324/AniWorld-Downloader/releases/latest) has standalone apps for Windows, Linux and macOS.

**Docker:**

```bash
docker pull ghcr.io/eierman324/aniworld-downloader:latest
```

or the [`docker-compose.yaml`](https://github.com/eierman324/AniWorld-Downloader/blob/feature/mediathekview/docker-compose.yaml) from the Mediathek branch, which already points at this image.

**Python** (3.11 or newer, plus [FFmpeg](https://ffmpeg.org/)), installed from a feature's branch. For the Mediathek:

```bash
python -m pip install "aniworld @ git+https://github.com/eierman324/AniWorld-Downloader.git@feature/mediathekview"
```

Start it with `aniworld -w` and open the **Mediathek** tab. To go back to the original: `python -m pip install --force-reinstall aniworld`.

## Branches

- `main`: this overview, nothing else.
- `models`: an unchanged mirror of the original.
- `feature/…`: one branch per feature.

## Issues

Problems with a feature from this fork go [here](https://github.com/eierman324/AniWorld-Downloader/issues). Anything about the app itself goes to the [original project](https://github.com/phoenixthrush/AniWorld-Downloader/issues).

## Credits and license

[AniWorld Downloader](https://github.com/phoenixthrush/AniWorld-Downloader) by phoenixthrush and its contributors, under the [MIT License](https://github.com/phoenixthrush/AniWorld-Downloader/blob/models/LICENSE). The features in this fork use the same license.
