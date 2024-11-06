"""preferences.py - viewer preferences (CONFIG_DIR/preferences.xml).

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


import os.path
import lxml.etree as xml

try:
  from . import constants
except Exception:
  import constants

class Preferences():

  def __init__(self):
      self.prefs_file_path = os.path.join(constants.CONFIG_DIR, 'preferences.xml');
      self.load_preferences()

  def create_new_tree(self):
      self.tree = xml.Element("preferences")

      version = xml.SubElement(self.tree, "version")
      version.text = constants.VERSION

      self.check_elements()

      #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))

  def load_preferences(self):
      if os.path.isfile(self.prefs_file_path):
        self.tree = xml.parse(source = self.prefs_file_path).getroot()
        self.set_value('version', constants.VERSION)
        self.check_elements()
        self.save_preferences()
      else:
        self.create_new_tree()
        f = open(self.prefs_file_path, 'w')
        print (xml.tostring(self.tree, encoding='unicode', pretty_print=True))
        f.write(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
        f.close()

  def save_preferences(self):
      f = open(self.prefs_file_path, 'w')
      f.write(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
      f.close()

  def get_value(self, element):
      if self.tree.find(element) != None:
        return self.tree.find(element).text
      else:
        self.set_default_value(element)
        return self.tree.find(element).text

  def set_value(self, element, value):
      self.tree.find(element).text = value
      return

  def save_library_filter(self, name, title, authors, series, genres, rating, characters, languages, publishdate, publisher, license, read, has_frames, im_format):
      # check if already exists
      for custom_filter in self.tree.find("library_custom_filters").findall("filter"):
        if custom_filter.get("name") == name:
          custom_filter.getparent().remove(custom_filter)

      # create new
      new_filter = xml.SubElement(self.tree.find("library_custom_filters"), "filter",
                                  name=name, title=title, authors=authors, series=series, genres=genres, rating=rating,
                                  characters=characters, languages=languages, publishdate=publishdate, publisher=publisher, license=license,
                                  read=read, has_frames=has_frames, im_format=im_format)
      return

  def remove_library_filter(self, name):
      # check if already exists
      for custom_filter in self.tree.find("library_custom_filters").findall("filter"):
        if custom_filter.get("name") == name:
          custom_filter.getparent().remove(custom_filter)

  def check_elements(self, *args):
      for element in ["bg_color", "fullscreen_toolbar_hiding", "image_resize_filter", "image_stretch", "scroll_step",
                      "popup_text_showing", "progress_bar_showing", "progress_bar_width", "progress_bar_color", "normal_font", "emphasis_font",
                      "strong_font", "code_font", "commentary_font", "font_color_default", "font_color_inverted", "library_books_per_page",
                      "library_cleanup", "library_layout", "library_default_sort_order", "library_custom_filters", "default_language",
                      "autorotate", "tmpfs", "crop_border", "animation", "animation_delay"]:
        if self.tree.find(element) == None:
          self.set_default_value(element)

  def set_default_value(self, element):
      if element == 'bg_color':
        bg_color = xml.SubElement(self.tree, "bg_color")
        bg_color.text = "#000000"
      elif element == 'fullscreen_toolbar_hiding':
        fullscreen_toolbar_hiding = xml.SubElement(self.tree, "fullscreen_toolbar_hiding")
        fullscreen_toolbar_hiding.text = "True"
      elif element == 'image_resize_filter':
        image_resize_filter = xml.SubElement(self.tree, "image_resize_filter")
        image_resize_filter.text = "0"
      elif element == 'image_stretch':
        image_stretch = xml.SubElement(self.tree, "image_stretch")
        image_stretch.text = "True"
      elif element == 'scroll_step':
        scroll_step = xml.SubElement(self.tree, "scroll_step")
        scroll_step.text = "2"
      elif element == 'popup_text_showing':
        popup_text_showing = xml.SubElement(self.tree, "popup_text_showing")
        popup_text_showing.text = "False"
      elif element == 'progress_bar_showing':
        progress_bar_showing = xml.SubElement(self.tree, "progress_bar_showing")
        progress_bar_showing.text = "True"
      elif element == 'progress_bar_width':
        progress_bar_width = xml.SubElement(self.tree, "progress_bar_width")
        progress_bar_width.text = "3"
      elif element == 'animation_delay':
        animation_delay = xml.SubElement(self.tree, "animation_delay")
        animation_delay.text = "3"
      elif element == 'progress_bar_color':
        progress_bar_color = xml.SubElement(self.tree, "progress_bar_color")
        progress_bar_color.text = "#aaaaaa"
      elif element == 'normal_font':
        normal_font = xml.SubElement(self.tree, "normal_font")
        normal_font.text = "Default"
      elif element == 'emphasis_font':
        emphasis_font = xml.SubElement(self.tree, "emphasis_font")
        emphasis_font.text = "Default"
      elif element == 'strong_font':
        strong_font = xml.SubElement(self.tree, "strong_font")
        strong_font.text = "Default"
      elif element == 'code_font':
        code_font = xml.SubElement(self.tree, "code_font")
        code_font.text = "Default"
      elif element == 'commentary_font':
        commentary_font = xml.SubElement(self.tree, "commentary_font")
        commentary_font.text = "Default"
      elif element == 'font_color_default':
        font_color_default = xml.SubElement(self.tree, "font_color_default")
        font_color_default.text = "#000000"
      elif element == 'font_color_inverted':
        font_color_default = xml.SubElement(self.tree, "font_color_inverted")
        font_color_default.text = "#ffffff"
      elif element == 'library_books_per_page':
        library_books_per_page = xml.SubElement(self.tree, "library_books_per_page")
        library_books_per_page.text = "5"
      elif element == 'library_cleanup':
        library_cleanup = xml.SubElement(self.tree, "library_cleanup")
        library_cleanup.text = "True"
      elif element == 'library_layout':
        library_layout = xml.SubElement(self.tree, "library_layout")
        library_layout.text = "0"
      elif element == 'library_default_sort_order':
        library_default_sort_order = xml.SubElement(self.tree, "library_default_sort_order")
        library_default_sort_order.text = "1"
      elif element == 'default_language':
        default_language = xml.SubElement(self.tree, "default_language")
        default_language.text = "0"
      elif element == 'autorotate':
        autorotate = xml.SubElement(self.tree, "autorotate")
        autorotate.text = "False"
      elif element == 'animation':
        autorotate = xml.SubElement(self.tree, "animation")
        autorotate.text = "True"
      elif element == 'tmpfs':
        """ Custom temp directory to be used instead of default system defined temp dir (when set to 'False').
            Can be set to /dev/shm for example to use tmpfs (temporary file storage filesystem, if supported by linux distribution),
            that uses RAM for temporary files storage. This may speed up opening and loading CBZ files and reduce disk I/Os
            but may fill in RAM and swap space quickly if large comicbook files are opened. So use with caution.
            To use this option, you need to edit the ~/.config/acbfv/preferences.xml file directly.
            ACBF Viewer creates acbfv directory here (e.g. /dev/shm/acbfv) where temporary files are stored. Anything inside
            acbfv directory is deleted when new CBZ file is opened, a CBZ file is added into library or ACBF Viewer is shut down properly.
        """
        tmpfs = xml.SubElement(self.tree, "tmpfs")
        tmpfs.text = "False"
      elif element == 'library_custom_filters':
        library_custom_filter = xml.SubElement(self.tree, "library_custom_filters")
      elif element == 'crop_border':
        crop_border = xml.SubElement(self.tree, "crop_border")
        crop_border.text = "False"

