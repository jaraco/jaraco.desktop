"""
`jaraco.util.wallpaper`

Based on nat-geo_background-setter.py by Samuel Huckins

This module contains routines to pull the latest National Geographic
"Picture of the Day" and set it as your desktop background. This module
may be executed directly.

The routine won't run if you are low on space, easily configurable below.

Assumes Gnome or Windows.
"""

from __future__ import division, print_function, unicode_literals

import os
import re
import sys
import urllib2
import ctypes
import subprocess
import collections

from BeautifulSoup import BeautifulSoup
from HTMLParser import HTMLParseError

from .itertools import last
from .string import local_format as lf

picture_dir = os.path.expanduser("~/Pictures/NatGeoPics")
# percentage of free space required on picture dir for the photo to be
#  downloaded.
free_space_minimum = 25
base_url = "http://photography.nationalgeographic.com/photography/photo-of-the-day"

#------------------------------------------------------------------------------

def _get_free_bytes_win32(dir):
	"""
	Return folder/drive free space and total space (in bytes)
	"""
	free_bytes = ctypes.c_ulonglong()
	total_bytes = ctypes.c_ulonglong()
	GetDiskFreeSpaceEx = ctypes.windll.kernel32.GetDiskFreeSpaceExW
	res = GetDiskFreeSpaceEx(unicode(dir), None,
		ctypes.byref(total_bytes), ctypes.byref(free_bytes))
	if not res:
		raise WindowsError("GetDiskFreeSpace failed")
	free_bytes = free_bytes.value
	total_bytes = total_bytes.value
	return free_bytes, total_bytes

def _get_free_bytes_default(dir):
	"""
	Return folder/drive free space and total space (in bytes)
	"""
	stat = os.statvfs(dir)
	free_bytes = stat.f_bsize * stat.f_bfree
	total_bytes = stat.f_bsize * stat.f_blocks
	return free_bytes, total_bytes

_get_free_bytes = globals().get('_get_free_bytes_' + sys.platform,
	_get_free_bytes_default)

def free_space(dir):
	"""
	Returns percentage of free space.
	"""
	try:
		free, total = _get_free_bytes(dir)
	except OSError:
		return False
	percen_free = free / total * 100
	return int(round(percen_free))

URLDetail = collections.namedtuple('URLDetail', 'url title')

def get_wallpaper_details(base_url):
	"""
	Finds the URL to download the wallpaper version of the image as well
	as the title shown on the page.
	Return URLDetail.

	>>> detail = get_wallpaper_details(base_url)
	>>> assert detail.url.startswith('http')
	>>> assert detail.title == detail.title.lower()
	"""
	try:
		html = urllib2.urlopen(base_url)
	except (urllib2.URLError, urllib2.HTTPError) as e:
		# Their server isn't responding, or in time, or the page is unavailable
		return False
	# Their pages write some script tags through document.write, which was
	# causing BeautifulSoup to choke
	html = b''.join(
		line for line in html
		if not b'document.write' in line
	)
	try:
		soup = BeautifulSoup(html)
	except HTMLParseError as e:
		print(e)
		raise SystemExit(4)

	# Find wallpaper image URL
	match = last(soup.findAll("div", {"class": "primary_photo"}))
	urls = [img['src'] for img in match.findAll('img')]
	if len(urls) != 1:
		return False
	url = urls[0]

	# Get main title
	match = last(soup.findAll("h1"))
	title = re.sub('[\W]+', '-', match.contents[0]).lower()

	return URLDetail(url, title)

def download_wallpaper(url, picture_dir, filename):
	"""
	Downloads URL passed, saves in specified location, cleans filename.
	"""
	filename = filename + "." + url.split(".")[-1]
	outpath = os.path.join(picture_dir, filename)
	try:
		f = urllib2.urlopen(url)
		print(lf("Downloading {url}"))
		with open(outpath, "wb") as local_file:
			local_file.write(f.read())
	except urllib2.HTTPError as e:
		print(lf("HTTP Error: {e.code} {url}"))
	except urllib2.URLError as e:
		print(lf("URL Error: {e.reason} {url}"))

	return outpath

def _set_wallpaper_linux2(filename):
	"""
	Sets the passed file as wallpaper.
	"""
	cmd = [
		'gconftool-2',
		'-t', 'str',
		'--set', '/desktop/gnome/background/picture_filename',
		filename,
	]
	subprocess.Popen(cmd)

def _set_wallpaper_win32(filename):
	SPI_SETDESKWALLPAPER = 0x14
	SPIF_UPDATEINIFILE = 0x1
	SPIF_SENDWININICHANGE = 0x2
	SystemParametersInfo = ctypes.windll.user32.SystemParametersInfoW
	SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, unicode(filename),
		SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE)

set_wallpaper = globals()['_set_wallpaper_' + sys.platform]

#------------------------------------------------------------------------------
def set_random_wallpaper():
	fs = free_space(picture_dir)
	if not fs:
		print(lf("{picture_dir} does not exist, please create."))
		raise SystemExit(1)
	if fs <= free_space_minimum:
		print(lf("Not enough free space in {picture_dir}! ({fs}% free)"))
		raise SystemExit(2)

	url, title = get_wallpaper_details(base_url)
	if not url:
		print("No wallpaper URL found.")
		raise SystemExit(3)

	filename = download_wallpaper(url, picture_dir, title)
	set_wallpaper(filename)

if __name__ == '__main__':
	set_random_wallpaper()
