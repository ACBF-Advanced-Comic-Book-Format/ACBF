"""Portability functions for ACBFV.

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
import tempfile
import lxml.etree as xml

def get_home_directory():
    """On UNIX-like systems, this method will return the path of the home
    directory, e.g. /home/username. On Windows, it will return a ACBFV
    sub-directory of <Documents and Settings/Username>.
    """
    if sys.platform == 'win32':
        return str(os.path.join(os.path.expanduser('~'), 'acbfa'))
    else:
        return str(os.path.expanduser('~'))


def get_config_directory():
    """Return the path to the ACBFA config directory. On UNIX, this will
    be $XDG_CONFIG_HOME/acbfa, on Windows it will be the same directory as
    get_home_directory().
    
    See http://standards.freedesktop.org/basedir-spec/latest/ for more
    information on the $XDG_CONFIG_HOME environmental variable.
    """
    if sys.platform == 'win32':
        return os.path.join(os.path.expanduser('~'), 'acbfa_conf')
    else:
        base_path = os.getenv('XDG_CONFIG_HOME',
            os.path.join(get_home_directory(), '.config'))
        return os.path.join(base_path, 'acbfa')


def get_data_directory():
    """Return the path to the ACBFA data directory. On UNIX, this will
    be /tmp/acbfa, on Windows it will be
    C:\Documents and settings\[user]\Application settings\Temp\acbfa.
    """

    return str(os.path.join(tempfile.gettempdir(), 'acbfa'))

def get_fonts_directory():
    font_dirs = []
    if sys.platform == 'win32':
        if os.getenv('CSIDL_FONTS') != None:
          font_dirs.append(os.getenv('CSIDL_FONTS'))
        else:
          font_dirs.append('C:\Windows\Fonts')
        return font_dirs
    elif sys.platform.startswith('linux'):
        if os.path.isfile('/etc/fonts/fonts.conf'):
          tree = xml.parse(source = '/etc/fonts/fonts.conf')
          for font_dir in tree.findall("dir"):
            font_dirs.append(font_dir.text.replace('~', os.path.expanduser('~')))
        else:
          if os.path.isdir('/usr/share/fonts'):
            font_dirs.append('/usr/share/fonts')
          if os.path.isdir('/usr/local/share/fonts'):
            font_dirs.append('/usr/local/share/fonts')
          if os.path.isdir('~/.fonts'):
            font_dirs.append(os.path.join(os.path.expanduser('~'), '.fonts'))
          if os.path.isdir('/system/fonts'):
            font_dirs.append('/system/fonts')

        return font_dirs

def get_platform():
    return sys.platform

