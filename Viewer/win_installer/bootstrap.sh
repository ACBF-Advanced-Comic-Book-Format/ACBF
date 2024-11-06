#!/usr/bin/env bash
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


set -e

function main {
    pacman --noconfirm -Suy

    pacman --noconfirm -S --needed \
        mingw-w64-i686-gtk3 \
        base-devel mingw-w64-i686-toolchain

    pacman --noconfirm -S --needed \
        mingw-w64-i686-python3 \
        mingw-w64-i686-python3-gobject \
        mingw-w64-i686-python3-pip \
        mingw-w64-i686-python3-lxml \
		mingw-w64-i686-python3-pillow \
		mingw-w64-i686-python3-matplotlib

    pip3 install --user -U patool
}

main;
