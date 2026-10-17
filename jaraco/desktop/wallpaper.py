"""
`jaraco.desktop.wallpaper`

Based on nat-geo_background-setter.py by Samuel Huckins

This module contains routines to pull the latest National Geographic
"Picture of the Day" and set it as your desktop background. This module
may be executed directly.

The routine won't run if you are low on space, easily configurable below.

Assumes Gnome or Windows.
"""

import ctypes
import html.parser
import os
import shutil
import subprocess
import sys
import urllib.request
from typing import NamedTuple

from bs4 import BeautifulSoup

picture_dir = os.path.expanduser("~/Pictures/NatGeoPics")
# percentage of free space required on picture dir for the photo to be
#  downloaded.
free_space_minimum = 25
base_url = "http://photography.nationalgeographic.com/photography/photo-of-the-day"

# ------------------------------------------------------------------------------


def free_space(dir):
    """
    Returns percentage of free space.

    >>> 0 <= free_space('.') <= 100
    True
    >>> free_space('/does/not/exist')
    False
    """
    try:
        usage = shutil.disk_usage(dir)
    except OSError:
        return False
    percen_free = usage.free / usage.total * 100
    return round(percen_free)


class URLDetail(NamedTuple):
    url: str
    title: str


def get_wallpaper_details(base_url):
    """
    Finds the URL to download the wallpaper version of the image as well
    as the title shown on the page.
    Return URLDetail.

    >>> detail = get_wallpaper_details(base_url)
    >>> assert detail.url.startswith('http')
    """
    try:
        res = urllib.request.urlopen(base_url)
    except (urllib.request.URLError, urllib.request.HTTPError):
        # Their server isn't responding, or in time, or the page is unavailable
        return False
    # Their pages write some script tags through document.write, which was
    # causing BeautifulSoup to choke
    content = b''.join(line for line in res if b'document.write' not in line)
    try:
        soup = BeautifulSoup(content, 'html.parser')
    except html.parser.HTMLParseError as e:
        print(e)
        raise SystemExit(4)

    # Find wallpaper image URL
    url = soup.find("meta", {"name": "twitter:image:src"})['content']
    title = soup.find("meta", {"name": "twitter:title"})['content']
    return URLDetail(url, title)


def download_wallpaper(url, picture_dir, filename):
    """
    Downloads URL passed, saves in specified location, cleans filename.
    """
    filename = filename + "." + url.split(".")[-1]
    outpath = os.path.join(picture_dir, filename)
    try:
        f = urllib.request.urlopen(url)
        print(f"Downloading {url}")
        with open(outpath, "wb") as local_file:
            local_file.write(f.read())
    except urllib.request.HTTPError as e:
        print(f"HTTP Error: {e.code} {url}")
    except urllib.request.URLError as e:
        print(f"URL Error: {e.reason} {url}")

    return outpath


def _set_wallpaper_linux(filename):
    """
    Sets the passed file as wallpaper.
    """
    cmd = [
        'gconftool-2',
        '-t',
        'str',
        '--set',
        '/desktop/gnome/background/picture_filename',
        filename,
    ]
    subprocess.Popen(cmd)


def _set_wallpaper_win32(filename):
    SPI_SETDESKWALLPAPER = 0x14
    SPIF_UPDATEINIFILE = 0x1
    SPIF_SENDWININICHANGE = 0x2
    SystemParametersInfo = ctypes.windll.user32.SystemParametersInfoW
    SystemParametersInfo(
        SPI_SETDESKWALLPAPER,
        0,
        str(filename),
        SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
    )


def _set_wallpaper_darwin(filename):
    cmd = [
        'defaults',
        'write',
        'com.apple.desktop',
        'Background',
        f'{{default = {{ImageFilePath = "{filename}"; }};}}',
    ]
    subprocess.check_call(cmd)


set_wallpaper = globals()['_set_wallpaper_' + sys.platform]


def set_random_wallpaper():
    fs = free_space(picture_dir)
    if not fs:
        print(f"{picture_dir} does not exist, please create.")
        raise SystemExit(1)
    if fs <= free_space_minimum:
        print(f"Not enough free space in {picture_dir}! ({fs}% free)")
        raise SystemExit(2)

    url, title = get_wallpaper_details(base_url)
    if not url:
        print("No wallpaper URL found.")
        raise SystemExit(3)

    filename = download_wallpaper(url, picture_dir, title)
    set_wallpaper(filename)


if __name__ == '__main__':
    set_random_wallpaper()
