# -*- coding: utf-8 -*-
# Copyright 2018 Robert Kubik
#
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

"""This file gets edited at build time to add build specific data. It is used for building Windows executable."""

BUILD_TYPE = u"default"
"""Either 'windows', 'windows-portable' or 'default'"""

BUILD_INFO = u""
"""Additional build info like bzr revision etc"""

BUILD_VERSION = 0
"""1.2.3 with a BUILD_VERSION of 1 results in 1.2.3.1"""
