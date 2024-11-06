"""history.py - tracks history of open files (CONFIG_DIR/history.xml).

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

class History():

  def __init__(self):
      self.hist_file_path = os.path.join(constants.CONFIG_DIR, 'history.xml');
      self.load_history()
      self.cleanup_history()

  def create_new_tree(self):
      self.tree = xml.Element("history")

      version = xml.SubElement(self.tree, "version")
      version.text = constants.VERSION

      self.save_history()
      self.load_history()

      #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))

  def load_history(self):
      try:
        self.tree = xml.parse(source = self.hist_file_path)
      except:
        self.create_new_tree()
        f = open(self.hist_file_path, 'w')
        f.write(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
        f.close()

  def save_history(self):
      f = open(self.hist_file_path, 'w')
      f.write(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
      f.close()

  def get_book_details(self, book_path):
      for book in self.tree.findall("file"):
        if book.get("path") == str(book_path):
          return (int(book.find("current_page").text), int(book.find("current_frame").text), int(book.find("current_zoom").text), int(book.find("current_language").text))
      return (1, 1, 1, 0)

  def set_book_details(self, book_path, current_page, current_frame, current_zoom, current_language):
      for book in self.tree.findall("file"):
        if book.get("path") == str(book_path):
          book.find("current_page").text = str(current_page)
          book.find("current_frame").text = str(current_frame)
          book.find("current_zoom").text = str(current_zoom)
          book.find("current_language").text = str(current_language) 
          return

      tree = xml.Element("history")
      version = xml.SubElement(tree, "version")
      version.text = constants.VERSION
      
      # copy old ones
      for book in self.tree.findall("file"):
        new_book = xml.SubElement(tree, "file", path=book.get("path"))
        new_page = xml.SubElement(new_book, "current_page")
        new_page.text = book.find("current_page").text
        new_page = xml.SubElement(new_book, "current_frame")
        new_page.text = book.find("current_frame").text
        new_page = xml.SubElement(new_book, "current_zoom")
        new_page.text = book.find("current_zoom").text
        new_page = xml.SubElement(new_book, "current_language")
        new_page.text = book.find("current_language").text
      

      # add new book
      new_book = xml.SubElement(tree, "file", path=str(book_path))
      new_page = xml.SubElement(new_book, "current_page")
      new_page.text = str(current_page)
      new_page = xml.SubElement(new_book, "current_frame")
      new_page.text = str(current_frame)
      new_page = xml.SubElement(new_book, "current_zoom")
      new_page.text = str(current_zoom)
      new_page = xml.SubElement(new_book, "current_language")
      new_page.text = str(current_language)

      self.tree = tree

      #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))

  def delete_book(self, path):
      for book in self.tree.findall("file"):
        if book.get("path") == str(path):
          book.getparent().remove(book)
      return

  def cleanup_history(self):
    deleted = False
    for book in self.tree.findall("file"):
      if not os.path.exists(book.get("path")):
        self.delete_book(str(book.get("path")))
        deleted = True

    if deleted:
      self.save_history()

