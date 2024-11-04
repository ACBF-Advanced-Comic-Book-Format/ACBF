"""library.py - Library Dialog.

Copyright (C) 2011-2024 Robert Kubik
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
from PIL import Image
import io
import base64
import shutil
import sys
from random import randint

try:
  from . import constants
  from . import fileprepare
  from . import acbfdocument
except Exception:
  import constants
  import fileprepare
  import acbfdocument

class Library():

  def __init__(self, library_dir):
      self.library_dir = library_dir
      self.prepared_file = None
      self.library_file_path = os.path.join(library_dir, 'library.xml');
      self.load_library()

  def create_new_tree(self):
      self.tree = xml.Element("library")

      version = xml.SubElement(self.tree, "version")
      version.text = constants.LIBRARY_VERSION

      library_info = xml.SubElement(self.tree, "library_info")

      #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
      
  def load_library(self):
      print('library - load_library')
      try:
        self.tree = xml.parse(source = self.library_file_path).getroot()
        if self.get_version() != constants.LIBRARY_VERSION:
           self.tree.find("version").text = constants.LIBRARY_VERSION
        if self.tree.find("library_info") == None:
          library_info = xml.SubElement(self.tree, "library_info")
      except Exception as err:
        print('Exception: ', err)
        self.create_new_tree()
        f = open(self.library_file_path, 'w')
        f.write(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
        f.close()

  def save_library(self):
      print('library - save_library')
      f = open(self.library_file_path, 'w')
      f.write(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
      f.close()
      
  def delete_book(self, path):
      print('library - delete_book')
      for book in self.tree.findall("book"):
        if book.get("path") == path:
          book.getparent().remove(book)
      return

  def get_version(self):
      if self.tree.find("version") != None:
        return self.tree.find("version").text
      else:
        return None

  def get_value(self, element, path):
      for book in self.tree.findall("book"):
        if book.get("path") == path:
          if book.find(element) != None:
            return book.find(element).text
          else:
            return None

  def set_value(self, element, value, path):
      for book in self.tree.findall("book"):
        if book.get("path") == path:
          if book.find(element) == None:
            new_element = xml.SubElement(book, element)
          book.find(element).text = value
          self.save_library()
      return

  def get_library_info_value(self, element):
      library_info = self.tree.find("library_info")
      if library_info.find(element) != None:
        return library_info.find(element).text
      else:
        return None

  def set_library_info_value(self, element, value):
      library_info = self.tree.find("library_info")
      if library_info.find(element) == None:
        new_element = xml.SubElement(library_info, element)
      library_info.find(element).text = value
      self.save_library()

  def check_books(self, *args):
      print('library - check_books')
      deleted = False
      for book in self.tree.findall("book"):
        if not os.path.exists(book.get("path") and '://' not in book.get("path")):
          self.delete_book(str(book.get("path")))
          deleted = True

      if deleted:
        self.save_library()

      # cleanup library covers directory
      if randint(0,9) == 0: #this is slow, therefore we do it once in 10 times
        for root, dirs, files in os.walk(os.path.join(self.library_dir, 'Covers')):
          for f in files:
            do_remove = True
            for book in self.tree.findall("book"):
              if str(os.path.join(root, f)) == book.find("coverpage").text:
                do_remove = False
            if do_remove:
              os.unlink(os.path.join(root, f))
          for d in dirs:
            if not os.listdir(os.path.join(root, d)):
              shutil.rmtree(os.path.join(root, d))

      return

  def sort_library(self, sort_key):
      print('library - sort_library')
      #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
      data = []
      for elem in self.tree.findall("book"):
        key = elem.findtext(sort_key)
        title = elem.findtext('title')
        if key == None or key == '':
          key = title
        elif sort_key == 'sequence' and key != '|': #sort by serie then by title
          key = key[:key.find('(') - 1] + key[key.find('(') + 1:key.find(')')].rjust(4, '0') + title

        #print(key, title)

        data.append((key, elem))
      data.sort()

      self.tree[:] = [item[-1] for item in data]
      version = xml.SubElement(self.tree, "version")
      version.text = constants.LIBRARY_VERSION
      library_info = xml.SubElement(self.tree, "library_info")
      #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))

  def insert_new_book(self, filename, library_dir, file_uri):
        print("library - insert_new_book")
        # check if already exists in library
        rating = '0'
        for book in self.tree.findall("book"):
          if book.get("path") == filename:
            return
          if book.get("path") == file_uri:
            return
        
        coverpage, book_title, publish_date, publisher, authors, genres, sequence, annotation, languages, characters, pages, license, has_frames = self.load_file(filename, library_dir)

        if book_title == {}:
          return False

        if file_uri != None:
          new_book = xml.SubElement(self.tree, "book", path=file_uri)
        else:
          new_book = xml.SubElement(self.tree, "book", path=filename)

        for title in book_title.items():
          new_book_title = xml.SubElement(new_book, "title", lang=title[0])
          new_book_title.text = title[1]

        new_authors = xml.SubElement(new_book, "authors")
        new_authors.text = authors

        new_publish_date = xml.SubElement(new_book, "publish_date")
        new_publish_date.text = publish_date

        new_publisher = xml.SubElement(new_book, "publisher")
        new_publisher.text = publisher

        new_sequence = xml.SubElement(new_book, "sequence")
        new_sequence.text = sequence

        for anno in annotation.items():
          new_annotation = xml.SubElement(new_book, "annotation", lang=anno[0])
          new_annotation.text = anno[1]

        new_languages = xml.SubElement(new_book, "languages")
        new_languages.text = languages

        new_genres = xml.SubElement(new_book, "genres")
        new_genres.text = genres

        new_characters = xml.SubElement(new_book, "characters")
        new_characters.text = characters

        new_rating = xml.SubElement(new_book, "rating")
        new_rating.text = rating

        new_pages = xml.SubElement(new_book, "pages")
        new_pages.text = str(pages)

        new_license = xml.SubElement(new_book, "license")
        new_license.text = license

        new_coverpage = xml.SubElement(new_book, "coverpage", type='link')
        new_coverpage.text = coverpage

        new_read_flag = xml.SubElement(new_book, "read")
        new_read_flag.text = "False"

        new_has_frames = xml.SubElement(new_book, "has_frames")
        new_has_frames.text = str(has_frames)

        return True

  def convert_webp(self, *args):
        im = Image.open(self.load_image).convert("RGB")
        self.load_image = self.load_image[:-5] + '.jpg'
        im.save(self.load_image,"jpeg")

  def load_file(self, in_filename, library_dir):
        print("library - load_file")
        fileprepare.FilePrepare(self, in_filename, library_dir, 'lib')
        self.tempdir = library_dir
        self.base_dir = os.path.dirname(in_filename)
        acbf_document = acbfdocument.ACBFDocument(self, self.prepared_file)
        
        if not acbf_document.valid:
          return None, None, None, None, None, None, None, None, None, None, None, None

        # coverpage
        self.load_image = acbf_document.coverpage
        if self.load_image[-4:].upper() == 'WEBP':
          self.convert_webp()

        coverpage = Image.open(self.load_image)
        coverpage.thumbnail((int(coverpage.size[0]*300/float(coverpage.size[1])),300), Image.NEAREST)
        output_directory = os.path.join(os.path.join(self.library_dir, 'Covers'), acbf_document.book_title[list(acbf_document.book_title.items())[0][0]][0].upper())
        if not os.path.exists(output_directory):
          os.makedirs(output_directory, 0o700)

        cover_number = 0
        for root, dirs, files in os.walk(output_directory):
          for f in files:
            if f[-4:].upper() == '.PNG' and f[:-4].isdigit():
              if cover_number < int(f[:-4]):
                cover_number = int(f[:-4])
        cover_filename = os.path.join(output_directory, str(cover_number + 1) + '.png')
        output = io.BytesIO()
        coverpage.save(output, "PNG")
        coverpage_base64 = base64.b64encode(output.getvalue())
        output.close()
        coverpage.save(cover_filename, "PNG")

        # sequences
        sequences = ''
        for sequence in acbf_document.sequences:
          sequences = sequences + sequence[0] + ' (' + sequence[1] + '), '
        sequences = sequences[:-2]

        # publish-date 
        if acbf_document.publish_date_value != '':
          publish_date = acbf_document.publish_date_value
        else:
          publish_date = '9999-01-01'

        # languages
        languages = ''
        for language in acbf_document.languages:
          if language[1] == 'FALSE' and language[0] == '??':
            languages = languages + '??(no text layer), '
          elif language[1] == 'FALSE':
            languages = languages + language[0] + '(no text layer), '
          else:
            languages = languages + language[0] + ', '
        languages = languages[:-2]

        # clear library temp directory
        for root, dirs, files in os.walk(library_dir):
          for f in files:
            os.unlink(os.path.join(root, f))
          for d in dirs:
            shutil.rmtree(os.path.join(root, d))

        return cover_filename, acbf_document.book_title, publish_date, acbf_document.publisher, acbf_document.authors, acbf_document.genres, sequences, acbf_document.annotation, languages, acbf_document.characters, acbf_document.pages_total, acbf_document.license, acbf_document.has_frames


# function to retrieve text value from element without throwing exception
def get_element_text(element_tree, element):
    try:
      text_value = element_tree.find('{http://www.fictionbook-lib.org/xml/acbf/1.0}' + element).text
      if text_value is None:
        text_value = ''
    except:
      text_value = ''
    return text_value

def get_element_text2(element_tree, element):
    try:
      text_value = element_tree.find(element).text
      if text_value is None:
        text_value = ''
    except:
      text_value = ''
    return text_value

