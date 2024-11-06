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
DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "${DIR}"

# CONFIG START

ARCH="i686"
BUILD_VERSION="0"

# CONFIG END

MISC="${DIR}"/misc
if [ "${ARCH}" = "x86_64" ]; then
    MINGW="mingw64"
else
    MINGW="mingw32"
fi

ACBF_VERSION="2.00"
ACBF_VERSION_DESC="UNKNOWN"

function set_build_root {
    BUILD_ROOT="$1"
    REPO_CLONE="${BUILD_ROOT}"/acbfv
    MINGW_ROOT="${BUILD_ROOT}/${MINGW}"
}

set_build_root "${DIR}/_build_root"

function build_pacman {
    pacman --root "${BUILD_ROOT}" "$@"
}

function build_pip {
    "${BUILD_ROOT}"/"${MINGW}"/bin/python3.exe -m pip "$@"
}

function build_python {
    "${BUILD_ROOT}"/"${MINGW}"/bin/python3.exe "$@"
}

function build_compileall {
    MSYSTEM= build_python -m compileall -b "$@"
}

function install_pre_deps {
    pacman -S --needed --noconfirm p7zip bzr dos2unix \
        mingw-w64-"${ARCH}"-nsis wget mingw-w64-"${ARCH}"-toolchain
}

function create_root {
    mkdir -p "${BUILD_ROOT}"

    mkdir -p "${BUILD_ROOT}"/var/lib/pacman
    mkdir -p "${BUILD_ROOT}"/var/log
    mkdir -p "${BUILD_ROOT}"/tmp

    build_pacman -Syu
    build_pacman --noconfirm -S base
}

function extract_installer {
    [ -z "$1" ] && (echo "Missing arg"; exit 1)

    mkdir -p "$BUILD_ROOT"
    7z x -o"$BUILD_ROOT"/"$MINGW" "$1"
    rm -rf "$MINGW_ROOT"/'$PLUGINSDIR' "$MINGW_ROOT"/*.txt "$MINGW_ROOT"/*.nsi
}

function install_deps {
    echo "install deps"
    # We don't use the fontconfig backend, and this skips the lengthy
    # cache update step during package installation
    export MSYS2_FC_CACHE_SKIP=1

	build_pacman --noconfirm -Sc
	
    build_pacman --noconfirm -S \
	    bzr \
        mingw-w64-"${ARCH}"-gtk3 \
        mingw-w64-"${ARCH}"-python3 \
		mingw-w64-"${ARCH}"-python3-numpy \
        mingw-w64-"${ARCH}"-python3-gobject \
        mingw-w64-"${ARCH}"-python3-pip \
		mingw-w64-"${ARCH}"-python3-lxml \
		mingw-w64-"${ARCH}"-python3-pillow \
		mingw-w64-"${ARCH}"-python3-pytest \
		mingw-w64-"${ARCH}"-python3-matplotlib

    PIP_REQUIREMENTS="\
patool==1.12
"

    build_pip install --no-deps --no-binary ":all:" --upgrade \
        --force-reinstall $(echo "$PIP_REQUIREMENTS" | tr ["\\n"] [" "])

    build_pacman --noconfirm -Rdds \
        mingw-w64-"${ARCH}"-shared-mime-info \
        mingw-w64-"${ARCH}"-python3-pip \
        mingw-w64-"${ARCH}"-ncurses \
        mingw-w64-"${ARCH}"-tk \
        mingw-w64-"${ARCH}"-tcl \
		mingw-w64-"${ARCH}"-python3-distlib
	
	#build_pacman --noconfirm -Rdds mingw-w64-"${ARCH}"-python2 || true

    #build_pacman -S --noconfirm mingw-w64-"${ARCH}"-python3-setuptools
}

function install_acbfv {
    rm -Rf "${REPO_CLONE}"
    bzr checkout --light lp:acbf "${REPO_CLONE}"
    build_python "${REPO_CLONE}"/Viewer/install.py install --dir "${MINGW_ROOT}"/lib/python3.7/site-packages

    # Create launchers
	
    python3 "${MISC}"/create-launcher.py \
        "1.0" "${MINGW_ROOT}"/bin
	
	build_compileall -d "" -f -q "$(cygpath -w "${MINGW_ROOT}")"
}

function cleanup_before {
    echo "cleanup_before"
    # these all have svg variants
    find "${MINGW_ROOT}"/share/icons -name "*.symbolic.png" -exec rm -f {} \;

    # remove some larger ones
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/512x512"
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/256x256"
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/96x96"
    rm -Rf "${MINGW_ROOT}/share/icons/Adwaita/48x48"
    "${MINGW_ROOT}"/bin/gtk-update-icon-cache-3.0.exe \
        "${MINGW_ROOT}"/share/icons/Adwaita

    # remove some gtk demo icons
    find "${MINGW_ROOT}"/share/icons/hicolor -name "gtk3-*" -exec rm -f {} \;
    "${MINGW_ROOT}"/bin/gtk-update-icon-cache-3.0.exe \
        "${MINGW_ROOT}"/share/icons/hicolor

	# cleanup libxslt
	find "${MINGW_ROOT}"/share/doc/libxslt-python*/examples -name "*.py" -exec rm -f {} \;
	
    # python related, before installing acbfv
    rm -Rf "${MINGW_ROOT}"/lib/python3.*/test
    rm -f "${MINGW_ROOT}"/lib/python3.*/lib-dynload/_tkinter*
    find "${MINGW_ROOT}"/lib/python3.*/lib2to3 -type d -name "test*" \
        -prune -exec rm -rf {} \;
    find "${MINGW_ROOT}"/lib/python3.* -type d -name "*_test*" \
        -prune -exec rm -rf {} \;

    find "${MINGW_ROOT}"/bin -name "*.pyo" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "*.pyc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -type d -name "__pycache__" -prune -exec rm -rf {} \;

    build_compileall -d "" -f -q "$(cygpath -w "${MINGW_ROOT}")"
    find "${MINGW_ROOT}" -name "*.py" -exec rm -f {} \;
	
	glib-compile-schemas "${MINGW_ROOT}"/share/glib-2.0/schemas/
}

function cleanup_after {
    # delete translations we don't support
    for d in "${MINGW_ROOT}"/share/locale/*/LC_MESSAGES; do
        if [ ! -f "${d}"/acbfv.mo ]; then
            rm -Rf "${d}"
        fi
    done

    find "${MINGW_ROOT}" -regextype "posix-extended" -name "*.exe" -a ! \
        -iregex ".*/(acbfv|exfalso|operon|python|gspawn-)[^/]*\\.exe" \
        -exec rm -f {} \;

    rm -Rf "${MINGW_ROOT}"/libexec
    rm -Rf "${MINGW_ROOT}"/share/gtk-doc
    rm -Rf "${MINGW_ROOT}"/include
    rm -Rf "${MINGW_ROOT}"/var
    rm -Rf "${MINGW_ROOT}"/etc
    rm -Rf "${MINGW_ROOT}"/share/zsh
    rm -Rf "${MINGW_ROOT}"/share/pixmaps
    rm -Rf "${MINGW_ROOT}"/share/gnome-shell
    rm -Rf "${MINGW_ROOT}"/share/dbus-1
    rm -Rf "${MINGW_ROOT}"/share/gir-1.0
    rm -Rf "${MINGW_ROOT}"/share/doc
    rm -Rf "${MINGW_ROOT}"/share/man
    rm -Rf "${MINGW_ROOT}"/share/info
    rm -Rf "${MINGW_ROOT}"/share/mime
    rm -Rf "${MINGW_ROOT}"/share/gettext
    rm -Rf "${MINGW_ROOT}"/share/libtool
    rm -Rf "${MINGW_ROOT}"/share/licenses
    rm -Rf "${MINGW_ROOT}"/share/appdata
    rm -Rf "${MINGW_ROOT}"/share/aclocal
    rm -Rf "${MINGW_ROOT}"/share/ffmpeg
    rm -Rf "${MINGW_ROOT}"/share/vala
    rm -Rf "${MINGW_ROOT}"/share/readline
    rm -Rf "${MINGW_ROOT}"/share/xml
    rm -Rf "${MINGW_ROOT}"/share/bash-completion
    rm -Rf "${MINGW_ROOT}"/share/common-lisp
    rm -Rf "${MINGW_ROOT}"/share/emacs
    rm -Rf "${MINGW_ROOT}"/share/gdb
    rm -Rf "${MINGW_ROOT}"/share/libcaca
    rm -Rf "${MINGW_ROOT}"/share/gettext
    rm -Rf "${MINGW_ROOT}"/share/gst-plugins-base
    rm -Rf "${MINGW_ROOT}"/share/gst-plugins-bad
    rm -Rf "${MINGW_ROOT}"/share/libgpg-error
    rm -Rf "${MINGW_ROOT}"/share/p11-kit
    rm -Rf "${MINGW_ROOT}"/share/pki
    rm -Rf "${MINGW_ROOT}"/share/thumbnailers
    rm -Rf "${MINGW_ROOT}"/share/gtk-3.0
    rm -Rf "${MINGW_ROOT}"/share/nghttp2
    rm -Rf "${MINGW_ROOT}"/share/themes
    rm -Rf "${MINGW_ROOT}"/share/fontconfig
    rm -Rf "${MINGW_ROOT}"/share/gettext-*
    rm -Rf "${MINGW_ROOT}"/share/gstreamer-1.0
    rm -Rf "${MINGW_ROOT}"/share/installed-tests

    find "${MINGW_ROOT}"/share/glib-2.0 -type f ! \
        -name "*.compiled" -exec rm -f {} \;

    rm -Rf "${MINGW_ROOT}"/lib/cmake
    rm -Rf "${MINGW_ROOT}"/lib/gettext
    rm -Rf "${MINGW_ROOT}"/lib/gtk-3.0
    rm -Rf "${MINGW_ROOT}"/lib/mpg123
    rm -Rf "${MINGW_ROOT}"/lib/p11-kit
    rm -Rf "${MINGW_ROOT}"/lib/pkcs11
    rm -Rf "${MINGW_ROOT}"/lib/ruby
    rm -Rf "${MINGW_ROOT}"/lib/engines

    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstvpx.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstdaala.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstdvdread.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopenal.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopenexr.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopenh264.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstresindvd.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstassrender.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstx265.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstwebp.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopengl.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstmxf.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstfaac.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstschro.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstrtmp.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstzbar.dll

    rm -f "${MINGW_ROOT}"/bin/libharfbuzz-icu-0.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstcacasink.dll
    rm -f "${MINGW_ROOT}"/bin/libgstopencv-1.0-0.dll
    rm -f "${MINGW_ROOT}"/lib/gstreamer-1.0/libgstopencv.dll
    rm -Rf "${MINGW_ROOT}"/lib/python2.*

    find "${MINGW_ROOT}" -name "*.a" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.whl" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.h" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.la" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.sh" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.jar" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.def" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.cmd" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.cmake" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.pc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.desktop" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.manifest" -exec rm -f {} \;
    find "${MINGW_ROOT}" -name "*.pyo" -exec rm -f {} \;

    find "${MINGW_ROOT}"/bin -name "*-config" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "easy_install*" -exec rm -f {} \;
    find "${MINGW_ROOT}" -regex ".*/bin/[^.]+" -exec rm -f {} \;
    find "${MINGW_ROOT}" -regex ".*/bin/[^.]+\\.[0-9]+" -exec rm -f {} \;

    find "${MINGW_ROOT}" -name "gtk30-properties.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "gettext-tools.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "libexif-12.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "xz.mo" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "libgpg-error.mo" -exec rm -rf {} \;

    find "${MINGW_ROOT}" -name "old_root.pem" -exec rm -rf {} \;
    find "${MINGW_ROOT}" -name "weak.pem" -exec rm -rf {} \;

    find "${MINGW_ROOT}"/bin -name "*.pyo" -exec rm -f {} \;
    find "${MINGW_ROOT}"/bin -name "*.pyc" -exec rm -f {} \;
    find "${MINGW_ROOT}" -type d -name "__pycache__" -prune -exec rm -rf {} \;

    find "${MINGW_ROOT}" -type d -empty -delete
	
}

function build_installer {
    BUILDPY=$(echo "${MINGW_ROOT}"/lib/python3.*/site-packages/share/acbfv/src)/build.py
    cp "${REPO_CLONE}"/Viewer/src/build.py "$BUILDPY"
    echo 'BUILD_TYPE = u"windows"' >> "$BUILDPY"
    echo "BUILD_VERSION = $BUILD_VERSION" >> "$BUILDPY"
    (cd $(dirname "$BUILDPY") && build_compileall -d "" -q -f -l .)
    rm -f "$BUILDPY"

    cp misc/acbfv.ico "${BUILD_ROOT}"
    (cd "$BUILD_ROOT" && makensis -NOCD -DVERSION="$ACBF_VERSION" "${MISC}"/win_installer.nsi)

    mv "$BUILD_ROOT/acbfv-LATEST.exe" "$DIR/acbfv-$ACBF_VERSION-installer.exe"
}

function build_portable_installer {
    BUILDPY=$(echo "${MINGW_ROOT}"/lib/python3.*/site-packages/share/acbfv/src)/build.py
    cp "${REPO_CLONE}"/Viewer/src/build.py "$BUILDPY"
    echo 'BUILD_TYPE = u"windows-portable"' >> "$BUILDPY"
    echo "BUILD_VERSION = $BUILD_VERSION" >> "$BUILDPY"
    (cd $(dirname "$BUILDPY") && build_compileall -d "" -q -f -l .)
    rm -f "$BUILDPY"

    local PORTABLE="$DIR/acbfv-$ACBF_VERSION_DESC-portable"

    rm -rf "$PORTABLE"
    mkdir "$PORTABLE"
    cp "$MISC"/acbfv.lnk "$PORTABLE"
    cp -RT "${MINGW_ROOT}" "$PORTABLE"/data

    rm -Rf 7zout 7z1604.exe
    7z a payload.7z "$PORTABLE"
    wget -P "$DIR" -c http://www.7-zip.org/a/7z1604.exe
    7z x -o7zout 7z1604.exe
    cat 7zout/7z.sfx payload.7z > "$PORTABLE".exe
    rm -Rf 7zout 7z1604.exe payload.7z "$PORTABLE"
}
