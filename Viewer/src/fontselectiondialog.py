"""fontselectiondialog.py - Miscellaneous constants.

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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import io
from PIL import Image, ImageDraw, ImageFont

try:
  from . import constants
except Exception:
  import constants

class FontSelectionDialog(gtk.Dialog):
    
    """Font Selection dialog."""
    
    def __init__(self, window, font_type, selected_font):
        self._window = window
        gtk.Dialog.__init__(self, 'Font Selection: ' + font_type, window, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
        self.set_resizable(True)
        self.set_border_width(8)
        self.font_type = font_type

        hbox = gtk.HBox(False, 10)

        # list of available fonts
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.ShadowType.ETCHED_IN)
        sw.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(250, 200)
        
        hbox.pack_start(sw, True, True, 0)

        store = self.create_model()

        self.treeView = gtk.TreeView(store)
        self.treeView.set_rules_hint(True)
        sw.add(self.treeView)
        
        self.treeView.set_cursor(selected_font, start_editing=True)

        self.create_columns(self.treeView)

        # font drawing
        vbox = gtk.VBox(False, 10)

        label = gtk.Label("Font Preview:")
        vbox.pack_start(label, True, True, 0)

        self.font_image = gtk.Image()
        self.font_image.set_from_stock(gtk.STOCK_BOLD, gtk.IconSize.LARGE_TOOLBAR)
        self.get_font_preview(constants.FONTS_LIST[self.treeView.get_cursor()[0][0]][1])

        vbox.pack_start(self.font_image, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)
        
        self.vbox.pack_start(hbox, True, True, 0)
        self.show_all()
        self.treeView.connect("cursor-changed", self.on_cursor_changed)
        self.treeView.connect("row-activated", self.on_activated)

        # adjust scroll window
        scroll_adjustment = self.treeView.get_cursor()[0][0]/float(len(constants.FONTS_LIST))*(self.treeView.get_vadjustment().get_upper() - self.treeView.get_vadjustment().get_lower())
        if scroll_adjustment > self.treeView.get_vadjustment().get_upper():
          scroll_adjustment = self.treeView.get_vadjustment().get_upper()
        self.treeView.get_vadjustment().set_value(scroll_adjustment)

        self.run()
        self.destroy()


    def create_model(self):
        store = gtk.ListStore(str)
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
            store.append([font[0].replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', '')])
        return store

    def create_columns(self, treeView):
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Font Name", rendererText, text=0)
        column.set_sort_column_id(0)
        treeView.append_column(column)

    def on_cursor_changed(self, widget, *args):
        self._window._window.preferences.set_value(self.font_type, constants.FONTS_LIST[widget.get_cursor()[0][0]][0])
        self.get_font_preview(constants.FONTS_LIST[widget.get_cursor()[0][0]][1])

    def on_activated(self, widget, *args):
        self._window._window.preferences.set_value(self.font_type, constants.FONTS_LIST[widget.get_cursor()[0][0]][0])
        gtk.Widget.destroy(self)

    def get_font_preview(self, font_path):
        font_image = Image.new("RGB", (200, 50), "#fff")
        draw = ImageDraw.Draw(font_image)
        font = ImageFont.truetype(font_path, 20)
        draw.text((10, 10), "AaBbCc DdEeFf", font=font, fill="#000")


        pixbuf_image = pil_to_pixbuf(font_image, "#000")
        self.font_image.set_from_pixbuf(pixbuf_image)
        


def pil_to_pixbuf(PILImage, BGColor):
    """Return a pixbuf created from the PIL <image>."""

    bcolor = (int(Gdk.color_parse(BGColor).red_float*255), int(Gdk.color_parse(BGColor).green_float*255), int(Gdk.color_parse(BGColor).blue_float*255))

    PILImage = PILImage.convert("RGBA")
    bg = Image.new("RGB", PILImage.size, bcolor)
    bg.paste(PILImage,PILImage)

    with io.BytesIO() as dummy_file:
      bg.save(dummy_file, "ppm")
      contents = dummy_file.getvalue()

    loader = GdkPixbuf.PixbufLoader()
    loader.write(contents)
    pixbuf = loader.get_pixbuf()
    loader.close()
    return pixbuf
