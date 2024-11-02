"""constants.py - Miscellaneous constants.

Copyright (C) 2011-2014 Robert Pastierovic
https://launchpad.net/~just-me
"""

# -------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# -------------------------------------------------------------------------


import os
import sys

try:
  from . import portability
except Exception:
  import portability

VERSION = '1.12'
LIBRARY_VERSION = '0.4'
HOME_DIR = portability.get_home_directory()
CONFIG_DIR = portability.get_config_directory()
DATA_DIR = portability.get_data_directory()
FONTS_DIR = portability.get_fonts_directory()
PLATFORM = portability.get_platform()

exec_path = os.path.abspath(sys.argv[0])
BASE_DIR = os.path.dirname(os.path.dirname(exec_path))

# set icons directory
ICON_PATH = ''
if os.path.isfile(os.path.join(BASE_DIR, 'images/acbfa.png')):
  ICON_PATH = os.path.join(BASE_DIR, 'images')
elif os.path.isfile(os.path.join(os.path.dirname(exec_path), 'images/acbfa.png')):
  ICON_PATH = os.path.join(os.path.dirname(exec_path), 'images')
else: # Try system directories.
  for prefix in ['/usr', '/usr/local', '/usr/X11R6']:
    if os.path.isfile(os.path.join(prefix, 'share/acbfv/images/acbfa.png')):
      ICON_PATH = os.path.join(prefix, 'share/acbfv/images')
      break

# load fonts
FONTS_LIST = []
default_font = ''
for font_dir in FONTS_DIR:
  for root, dirs, files in os.walk(font_dir):
    for f in files:
      is_duplicate = False
      if f.upper()[-4:] == '.TTF' or f.upper()[-4:] == '.OTF':
        for font in FONTS_LIST:
          if f.upper() == font[0].upper():
            is_duplicate = True
        if not is_duplicate:
          FONTS_LIST.append((f, os.path.join(root, f)))
        # try to set default font
        if f in ('DejaVuSans-Bold.ttf', 'Arial_Bold.ttf', 'DroidSans.ttf'):
          default_font = os.path.join(root, f)

if default_font == '':
  default_font = FONTS_LIST[0][1]
sorted_list = sorted(FONTS_LIST, key=lambda font_name: font_name[0].upper())

FONTS_LIST = [('Default', default_font)]
for font in sorted_list:
  FONTS_LIST.append(font)

print("Default font:", default_font)

# languages
LANGUAGES = ['??#', 'aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv', 'dz', 'ee', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ch', 'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mr', 'ms', 'mt', 'my', 'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu']
