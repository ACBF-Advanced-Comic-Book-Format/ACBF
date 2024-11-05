"""settingsjson.py - app settings

Copyright (C) 2011-2024 Robert Kubik
https://github.com/GeoRW/ACBF
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

import json
from kivy.utils import platform

try:
  from . import constants
except Exception:
  import constants

if platform == 'android':
  from jnius import autoclass, cast
  PythonActivity = autoclass('org.kivy.android.PythonActivity')
  activity = cast('android.app.Activity', PythonActivity.mActivity)
  manager = activity.getPackageManager()
  info = manager.getPackageInfo(activity.getPackageName(), 0);
  version = info.versionName
  lib_path_type = 'string'
  lib_path_disabled = True
  lib_path_change_disabled = False
else:
  version = '0'
  lib_path_type = 'icon_path'
  lib_path_disabled = False
  lib_path_change_disabled = True
  print("Not running on Android ...")

fonts_list = []
for font in constants.FONTS_LIST:
  fonts_list.append(font[0])

max_covers_list = ['3', '4', '5', '6', '7', '8', '9', '10']
resize_filter_list = ['Nearest (fastest)', 'Bilinear', 'Bicubic', 'Antialias (best quality)']
iconset_list = ['Default', '3DGlossy', 'Clean3D', 'Ravenna3D']
transitions_list = ['None', 'Fade Out', 'Blend', 'Scroll Right']

lib_json = json.dumps([
{'type': 'bool',
'title': 'Zoom to frame',
'desc': 'Zoom to frame level by default when opening a book with frames defined.',
'section': 'general',
'key': 'zoom_to_frame'},
{'type': 'bool',
'title': 'Keep Screen On',
'desc': 'Keep the screen on while reading.',
'section': 'general',
'key': 'keep_screen_on'},
{'type': 'bool',
'title': 'Lock Page on Whole Page View',
'desc': 'Lock page when comic is zoomed out showing the whole page.',
'section': 'general',
'key': 'lock_page'},
{'type': 'bool',
'title': 'Use Custom Temporary Directory',
'desc': 'Use Custom Temporary Directory to store temporary files (large comics may need more space than internal card can handle).',
'section': 'general',
'key': 'use_temp_dir'},
{'type': 'icon_path',
'title': 'Temporary Directory',
'desc': 'Path where temporary files are stored.',
'disabled': True,
'section': 'general',
'key': 'temp_dir_path'},
{'type': 'scrolloptions',
'title': 'Icon Set',
'desc': 'Icon set to render application icons.',
'section': 'general',
'key': 'iconset',
'options': iconset_list},


{'type': 'title',
'title': 'Library'},
{'type': 'bool',
'title': 'Change Library Folder',
'desc': 'Change path to your comics folder.',
'section': 'general',
'disabled': lib_path_change_disabled,
'key': 'lib_path_change'},
{'type': lib_path_type,
'title': 'Comics Path',
'desc': 'Path where comics are stored',
'section': 'general',
'disabled': lib_path_disabled,
'key': 'lib_path'},
{'type': 'scrolloptions',
'title': 'Covers per Row',
'desc': 'Maximum number of covers to fit in one row.',
'section': 'general',
'key': 'max_covers',
'options': max_covers_list},

{'type': 'title',
'title': 'About'},
{'type': 'string',
'title': 'Version',
'desc': version,
'disabled': True,
'section': 'general',
'key': 'version'},
{'type': 'string',
'title': 'Copyright',
'desc': '(c) 2015-2018 Robert Kubik (www.launchpad.net/acbf).\n3DGlossy icons created by Aha-Soft (www.aha-soft.com), Creative Commons - Attribution 3.0 United States license.\nClean3D icons created by Mysitemyway.com, Creative Commons - Attribution 4.0 license.\nNuoveXT icons under GNU General Public License.\nRavenna3D icons by Double-J Design (http://www.doublejdesign.co.uk), Creative Common 3.0 Attribution license.',
'disabled': True,
'section': 'general',
'key': 'copyright'},
{'type': 'string',
'title': 'Threads',
'desc': 'Dynamic setting for number of threads for loading files.',
'disabled': True,
'section': 'general',
'key': 'threads'}
])

image_json = json.dumps([
{'type': 'scrolloptions',
'title': 'Page transition',
'desc': 'Animation type for page transitions',
'section': 'image',
'key': 'transition',
'options': transitions_list},
{'type': 'numeric',
'title': 'Animation duration',
'desc': 'Duration of page transition, zoom and scrolling animations (in seconds).',
'section': 'image',
'key': 'anim_dur'},
{'type': 'scrolloptions',
'title': 'Resize Filter',
'desc': 'Resize filter to use when resizing large images.',
'section': 'image',
'key': 'resize_filter',
'options': resize_filter_list},

{'type': 'title',
'title': 'Fonts'},
{'type': 'scrolloptions',
'title': 'Normal Font',
'desc': 'Default font to render language layers.',
'section': 'image',
'key': 'normal_font',
'options': fonts_list},
{'type': 'scrolloptions',
'title': 'Strong Font',
'desc': 'Font to render <strong> semantic tag in language layers.',
'section': 'image',
'key': 'strong_font',
'options': fonts_list},
{'type': 'scrolloptions',
'title': 'Emphasis Font',
'desc': 'Font to render <emphasis> semantic tag in language layers.',
'section': 'image',
'key': 'emphasis_font',
'options': fonts_list},
{'type': 'scrolloptions',
'title': 'Code Font',
'desc': 'Font to render <code> semantic tag in language layers.',
'section': 'image',
'key': 'code_font',
'options': fonts_list},
{'type': 'scrolloptions',
'title': 'Commentary Font',
'desc': 'Font to render <commentary> semantic tag in language layers.',
'section': 'image',
'key': 'commentary_font',
'options': fonts_list},
{'type': 'scrolloptions',
'title': 'Default Text Layer',
'desc': 'Default text layer to render when available.',
'section': 'image',
'key': 'default_text_layer',
'options': constants.LANGUAGES}
])

