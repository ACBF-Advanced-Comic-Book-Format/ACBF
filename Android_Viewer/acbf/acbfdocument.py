"""acbfdocument.py - ACBF Document object.

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

import os.path
import shutil
import lxml.etree as xml
from lxml import objectify
import base64
from PIL import Image
from xml.sax.saxutils import escape
import io
import urllib.request, urllib.parse, urllib.error
import re
import zipfile

try:
  from . import constants
except Exception:
  import constants

class ACBFDocument():

    def __init__(self, window,
                       filename):
        self._window = window
        self.coverpage = None
        self.cover_thumb = None
        self.pages_total = 0
        self.bg_color = '#000000'
        self.valid = False
        self.filename = filename
        self.authors = self.genres = self.keywords = self.characters = self.databaseref = ''
        self.publisher = self.publish_date = self.city = self.isbn = self.license = self.publish_date_value = ''
        self.doc_authors = self.creation_date = self.source = self.id = self.version = self.history = ''
        self.languages = [('??', 'FALSE')]
        self.contents_table = self.sequences = []
        self.book_title = self.annotation = self.genres_dict = {}
        self.has_frames = False
        self.fonts_dir = os.path.join(self._window.tempdir, 'Fonts')
        self.font_styles = {'normal': '', 'emphasis': '', 'strong': '', 'code': '', 'commentary': '', 'sign': '', 'formal': '', 'heading': '', 'letter': '', 'audio': '', 'thought': ''}
        self.font_colors = {'inverted': '#FFFFFF', 'speech': '#000000', 'code': '#000000', 'commentary': '#000000', 'sign': '#000000', 'formal': '#000000', 'heading': '#000000', 'letter': '#000000', 'audio': '#000000', 'thought': '#000000'}
        for style in ['normal', 'emphasis', 'strong', 'code', 'commentary', 'sign', 'formal', 'heading', 'letter', 'audio', 'thought']:
          self.font_styles[style] = constants.default_font
        
        try:
            self.base_dir = os.path.dirname(filename)
            self.tree = xml.parse(source = filename)
            root = self.tree.getroot()

            for elem in root.getiterator():
              i = elem.tag.find('}')
              if i >= 0:
                elem.tag = elem.tag[i+1:]
            objectify.deannotate(root)

            #print(xml.tostring(self.tree, encoding='unicode', pretty_print=True))
            self.bookinfo = self.tree.find("meta-data/book-info")
            self.publishinfo = self.tree.find("meta-data/publish-info")
            self.docinfo = self.tree.find("meta-data/document-info")
            self.references = self.tree.find("references")
            self.bg_color = self.tree.find("body").get("bgcolor")
            if self.bg_color == None:
              self.bg_color = '#000000'
            self.pages = self.tree.findall("body/" + "page")
            self.pages_total = len(self.pages)
            self.binaries = self.tree.findall("data/" + "binary")
            self.load_metadata()
            self.get_contents_table()
            self.extract_fonts()
            self.stylesheet = self.tree.find("style")
            if self.stylesheet != None:
              self.load_stylesheet()
            self.tree = None # keep memory usage low
            self.valid = True
        except Exception as inst:
            print("Unable to open ACBF file: %s %s" % (filename, inst))
            self.valid = False
            return

    def load_metadata(self):
        self.authors = self.genres = self.keywords = self.characters = self.databaseref = ''
        self.publisher = self.publish_date = self.city = self.isbn = self.license = self.publish_date_value = ''
        self.doc_authors = self.creation_date = self.source = self.id = self.version = self.history = ''
        self.book_title = {}
        self.annotation = {}
        self.genres_dict = {}

        # get coverpage
        image_id = self.bookinfo.find("coverpage/" + "image").get("href")
        image_uri = ImageURI(image_id)
        self.coverpage = self.load_image(image_uri)
        
        # get authors
        for author in self.bookinfo.findall("author"):
          home_page = ''
          email = ''
          for element in ['first-name', 'middle-name', 'nickname', 'last-name', 'home-page', 'email']:
            name = get_element_text(author, element)
            if element == 'home-page' and name != '':
              home_page = name
            elif element == 'email' and name != '':
              email = name
            elif name != '':
              self.authors = self.authors + name + ' '
          activity = author.get("activity")
          tr_lang = author.get("lang")
          if activity is not None or home_page != '' or email != '':
            self.authors = self.authors + '('
            if activity is not None:
              self.authors = self.authors + activity
              if activity == 'Translator' and tr_lang is not None:
                self.authors = self.authors + ' - ' + tr_lang 
            if home_page != '':
              self.authors = self.authors + ', ' + home_page
            if email != '':
              self.authors = self.authors + ', ' + email
            self.authors = self.authors + ') '
          self.authors = self.authors[:-1] + ', '
        self.authors = self.authors[:-2].replace('(, ', '(')

        # book-title
        for title in self.bookinfo.findall("book-title"):
          if title.get("lang") == None or title.get("lang") == 'en':
            self.book_title['en'] = escape(title.text)
          else:
            if title.text == None:
              self.book_title[title.get("lang")] = ''
            else:
              self.book_title[title.get("lang")] = escape(title.text)
        if self.book_title == {}:
          self.book_title['??'] = escape(os.path.basename(self.filename))[:-5]

        # genres
        for genre in self.bookinfo.findall("genre"):
          self.genres = self.genres + genre.text + ', '
        self.genres = self.genres[:-2]
        
        for genre in self.bookinfo.findall("genre"):
          if genre.get("match") == None:
            self.genres_dict[genre.text] = 100
          else:
            self.genres_dict[genre.text] = int(genre.get("match"))

        # languages
        self.languages = []
        for language in self.bookinfo.findall("languages/" + "text-layer"):
          self.languages.append((language.get("lang"), language.get("show").upper()))
        if len(self.languages) == 0:
          self.languages.append(('??', 'FALSE'))

        # annotation
        for annotation in self.bookinfo.findall("annotation"):
          annotation_text = ''
          for line in annotation.findall("p"):
            if line.text != None:
              annotation_text = annotation_text + line.text + '\n'
          annotation_text = escape(annotation_text[:-1])

          if annotation.get("lang") == None or annotation.get("lang") == 'en':
            self.annotation['en'] = annotation_text
          else:
            self.annotation[annotation.get("lang")] = annotation_text

        # keywords
        self.keywords = get_element_text(self.bookinfo, 'keywords')

        # sequence
        self.sequences = []
        for sequence in self.bookinfo.findall("sequence"):
          if sequence.text != None and sequence.get("title") != None:
            self.sequences.append((escape(sequence.get("title")), sequence.text))

        # databaseref
        for line in self.bookinfo.findall("databaseref"):
          if line.text != None:
            self.databaseref = self.databaseref + line.get("dbname") +  ' (' + line.get("type") + '): ' + line.text + '\n'
        self.databaseref = self.databaseref[:-2]

        #characters
        for line in self.bookinfo.findall("characters/" + "name"):
          if line.text != None:
            self.characters = self.characters + line.text + ', '
        self.characters = self.characters[:-2]

        # publish-info
        self.publisher = get_element_text(self.publishinfo, 'publisher')
        if self.publishinfo.find("publish-date") != None:
          if self.publishinfo.find("publish-date").get("value") != None:
            self.publish_date_value = self.publishinfo.find("publish-date").get("value")
            self.publish_date = ' (' + self.publish_date_value + ')'
          self.publish_date = get_element_text(self.publishinfo, 'publish-date') + self.publish_date
        self.city = get_element_text(self.publishinfo, 'city')
        self.isbn = get_element_text(self.publishinfo, 'isbn')
        self.license = get_element_text(self.publishinfo, 'license')

        # document-info
        for doc_author in self.docinfo.findall("author"):
          for element in ['first-name', 'middle-name', 'nickname', 'last-name']:
            name = get_element_text(doc_author,element)
            if name != '':
              self.doc_authors = self.doc_authors + name + ' '
          self.doc_authors = self.doc_authors[:-1] + ', '
        self.doc_authors = self.doc_authors[:-2]

        self.creation_date = get_element_text(self.docinfo, 'creation-date')

        for line in self.docinfo.findall("source/" + "p"):
          if line.text != None:
            self.source = self.source + line.text + '\n'
        self.source = self.source[:-1]

        self.id = get_element_text(self.docinfo, 'id')
        self.version = get_element_text(self.docinfo, 'version')

        for line in self.docinfo.findall("history/" + "p"):
          if line.text != None:
            self.history = self.history + line.text + '\n'
        self.history = self.history[:-1]

        # has frames
        for page in self.pages:
          for frame in page.findall("frame"):
            self.has_frames = True

    def load_image(self, image_uri):
        #print (image_uri.file_type, image_uri.archive_path, image_uri.file_path, self._window.tempdir, self._window.base_dir)
        try:
          if image_uri.file_type == "embedded":
            for image in self.binaries:
              if image.get("id") == image_uri.file_path:
                decoded = base64.b64decode(image.text)
                return_image = os.path.join(self.base_dir, image_uri.file_path)
                file_ = open(return_image, 'w')
                file_.write(decoded)
                file_.close()
                return return_image
          elif image_uri.file_type == "zip":
            z = zipfile.ZipFile(os.path.join(self._window.base_dir, image_uri.archive_path))
            z.extract(image_uri.file_path, self._window.tempdir)
            return os.path.join(self._window.tempdir, image_uri.file_path)
          elif image_uri.file_type == "http":
              try:
                http_image = image_uri.file_path
                return http_image
              except:
                print("Error loading image:", image_uri.file_path)
          else:
            return os.path.join(self.base_dir, image_uri.file_path)

        except Exception as inst:
          print("Unable to read image: %s" % inst)
          return './images/default.png'

    def load_page_image(self, page_num = 1):
        if page_num == 1:
          pilBackgroundImage = self.coverpage
          page_bg_color = '#000000'
        else:
          image_id = self.pages[page_num - 2].find("image").get("href")
          page_bg_color = self.pages[page_num - 2].get("bgcolor")
          if page_bg_color == None:
            page_bg_color = self.bg_color

          image_uri = ImageURI(image_id)
          pilBackgroundImage = self.load_image(image_uri)

        return pilBackgroundImage, page_bg_color

    def load_page_frames(self, page_num = 1):
        if page_num == 1:
          xml_frames = self.bookinfo.findall("coverpage/" + "frame")
          if xml_frames == None:
            return []
        else:
          xml_frames = self.pages[page_num - 2].findall("frame")
        frames = []
        coordinate_list = []
        for frame in xml_frames:
          for coordinate in frame.get("points").split(' '):
            coordinate_tuple = (int(coordinate.split(',')[0]), int(coordinate.split(',')[1]))
            coordinate_list.append(coordinate_tuple)
          frame_tuple = (coordinate_list, frame.get("bgcolor"))
          frames.append(frame_tuple)
          coordinate_list = []
        return frames

    def load_page_texts(self, page_num, language):
        text_areas = []
        references = []
        all_lines = ''
        text_rotation = 0
        area_type = 'speech'
        inverted = False
        if page_num == 1:
          return text_areas, references
        for text_layer in self.pages[page_num - 2].findall("text-layer"):
          if text_layer.get("bgcolor") != None:
            bgcolor_layer = text_layer.get("bgcolor")
          else:
            bgcolor_layer = '#ffffff'
          if text_layer.get("lang") == language:
            for text_area in text_layer.findall("text-area"):
              if text_area.get("bgcolor") != None:
                bgcolor = text_area.get("bgcolor")
              else:
                bgcolor = bgcolor_layer
              if text_area.get("text-rotation") != None:
                text_rotation = int(text_area.get("text-rotation"))
              else:
                text_rotation = 0
              if text_area.get("type") != None:
                area_type = text_area.get("type")
              else:
                area_type = 'speech'
              if text_area.get("inverted") == None:
                inverted = False
              elif text_area.get("inverted").upper() == 'TRUE':
                inverted = True
              else:
                inverted = False
              if text_area.get("transparent") == None:
                transparent = False
              elif text_area.get("transparent").upper() == 'TRUE':
                transparent = True
              else:
                transparent = False
              coordinate_list = []
              area_text = u''
              for coordinate in text_area.get("points").split(' '):
                coordinate_tuple = (int(coordinate.split(',')[0]), int(coordinate.split(',')[1]))
                coordinate_list.append(coordinate_tuple)
              for paragraph in text_area.findall("p"):
                paragraph_unicode = xml.tostring(paragraph, encoding='unicode')
                paragraph_end = paragraph_unicode.find('</p>') + 4
                paragraph_unicode = paragraph_unicode[0:paragraph_end]
                area_text = area_text + re.sub(r'<p[^>]*>', "", paragraph_unicode).replace(u'</p>', u' <BR>')
                # references
                for reference in paragraph.findall("a"):
                  for item in self.references.findall("reference"):
                    if item.get("id") == reference.get("href")[1:]:
                      all_lines = ''
                      for line in item.findall("p"):
                        all_lines = all_lines + line.text + '\n'
                      all_lines = all_lines[:-2]
                      references.append((reference.get("href")[1:], all_lines))
                for commentary in paragraph.findall("commentary"): 
                  for reference in commentary.findall("a"):
                    for item in self.references.findall("reference"):
                      if item.get("id") == reference.get("href")[1:]:
                        all_lines = ''
                        for line in item.findall("p"):
                          all_lines = all_lines + line.text + '\n'
                        all_lines = all_lines[:-2]
                        references.append((reference.get("href")[1:], all_lines))

              area_text = area_text[:-5]
              text_area_tuple = (coordinate_list, area_text, bgcolor, text_rotation, area_type, inverted, transparent)
              text_areas.append(text_area_tuple)

        #print(xml.tostring(text_areas[0][1][0], encoding='unicode', pretty_print=True))

        return text_areas, references

    def get_page_transition(self, page_num):
        if self.pages[page_num - 2].get("transition") == None:
          return 'undefined'
        else:
          return self.pages[page_num - 2].get("transition")

    def get_contents_table(self):
        self.contents_table = []
        for lang in self.languages:
          contents = []
          for idx, page in enumerate(self.pages, start = 2):
            for title in page.findall("title"):
              if ((title.get("lang") == lang[0]) or (title.get("lang") == None)):
                contents.append((title.text, str(idx)))
          if len(contents) > 0:
            self.contents_table.append(contents)

    def load_stylesheet(self):
        #print(self.stylesheet.text)
        #sheet = cssutils.parseString(self.stylesheet.text)
        font = ''

        for rule in self.stylesheet.text.replace('\n', ' ').split('}'):
          if rule.strip() != '':
            selector = rule.strip().split('{')[0].strip().upper()
            #print("selectorText: ", selector)
            font_style = 'normal'
            font_weight = 'normal'
            font_stretch = 'normal'
            font_families = ''
            for style in rule.strip().split('{')[1].strip().split(';'):
              if style != '':
                #print("style:", style.split(':')[0].strip())
                #print("value:", style.split(':')[1].strip())
                current_style = style.split(':')[0].strip().upper()
                if current_style == 'FONT-FAMILY':
                  font_families = style.split(':')[1].strip()
                elif current_style == 'FONT-STYLE':
                  font_style = style.split(':')[1].strip()
                elif current_style == 'FONT-WEIGHT':
                  font_weight = style.split(':')[1].strip()
                elif current_style == 'FONT-SRTRETCH':
                  font_stretch = style.split(':')[1].strip()

                if selector == '*' and current_style == 'COLOR':
                  self.font_colors['speech'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA' and current_style == 'COLOR':
                  self.font_colors['speech'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[INVERTED=TRUE]' and current_style == 'COLOR':
                  self.font_colors['inverted'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=SPEECH]' and current_style == 'COLOR':
                  self.font_colors['speech'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=COMMENTARY]' and current_style == 'COLOR':
                  self.font_colors['commentary'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=FORMAL]' and current_style == 'COLOR':
                  self.font_colors['formal'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=LETTER]' and current_style == 'COLOR':
                  self.font_colors['letter'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=CODE]' and current_style == 'COLOR':
                  self.font_colors['code'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=HEADING]' and current_style == 'COLOR':
                  self.font_colors['heading'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=AUDIO]' and current_style == 'COLOR':
                  self.font_colors['audio'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=THOUGHT]' and current_style == 'COLOR':
                  self.font_colors['thought'] = style.split(':')[1].strip().strip('"')
                elif selector == 'TEXT-AREA[TYPE=SIGN]' and current_style == 'COLOR':
                  self.font_colors['sign'] = style.split(':')[1].strip().strip('"')

            if font_families != '':
              for font_family in font_families.split(','):
                #check if font exists in acbf document
                font_family_stripped = font_family.strip().strip('"')
                if os.path.isfile(os.path.join(self.fonts_dir, font_family_stripped)):
                  font = os.path.join(self.fonts_dir, font_family_stripped)
                  break

            if selector in ('P', 'TEXT-AREA') and font != '':
              self.font_styles['normal'] = font
            elif selector == 'EMPHASIS' and font != '':
              self.font_styles['emphasis'] = font
            elif selector == 'STRONG' and font != '':
              self.font_styles['strong'] = font
            elif selector in ('CODE', 'TEXT-AREA[TYPE=CODE]', 'TEXT-AREA[TYPE="CODE"]') and font != '':
              self.font_styles['code'] = font
            elif selector in ('COMMENTARY', 'TEXT-AREA[TYPE=COMMENTARY]', 'TEXT-AREA[TYPE="COMMENTARY"]') and font != '':
              self.font_styles['commentary'] = font
            elif selector in ('TEXT-AREA[TYPE=SIGN]', 'TEXT-AREA[TYPE="SIGN"]') and font != '':
              self.font_styles['sign'] = font
            elif selector in ('TEXT-AREA[TYPE=FORMAL]', 'TEXT-AREA[TYPE="FORMAL"]') and font != '':
              self.font_styles['formal'] = font
            elif selector in ('TEXT-AREA[TYPE=HEADING]', 'TEXT-AREA[TYPE="HEADING"]') and font != '':
              self.font_styles['heading'] = font
            elif selector in ('TEXT-AREA[TYPE=LETTER]', 'TEXT-AREA[TYPE="LETTER"]') and font != '':
              self.font_styles['letter'] = font
            elif selector in ('TEXT-AREA[TYPE=AUDIO]', 'TEXT-AREA[TYPE="AUDIO"]') and font != '':
              self.font_styles['audio'] = font
            elif selector in ('TEXT-AREA[TYPE=THOUGHT]', 'TEXT-AREA[TYPE="THOUGHT"]') and font != '':
              self.font_styles['thought'] = font

        for style in ['emphasis', 'strong', 'code', 'commentary', 'sign', 'formal', 'heading', 'letter', 'audio', 'thought']:
          if self.font_styles[style] == '':
            self.font_styles[style] = self.font_styles['normal']
        #print(self.font_styles)

    def extract_fonts(self):
      if os.path.exists(os.path.join(self.base_dir, 'Fonts')) and not os.path.exists(self.fonts_dir):
        shutil.copytree(os.path.join(self.base_dir, 'Fonts'), self.fonts_dir)
      if not os.path.exists(self.fonts_dir):
        os.makedirs(self.fonts_dir, 0o700)
      for font in self.binaries:
        if font.get("content-type") == 'application/font-sfnt':
          decoded = base64.b64decode(font.text)
          f = open(os.path.join(self.fonts_dir, font.get("id")), 'wb')
          f.write(decoded)
          f.close()

class ImageURI():

    def __init__(self, input_path):
        self.file_type = 'unknown'
        self.archive_path = ''
        self.file_path = ''

        if input_path[0:3] == 'zip':
          self.file_type = 'zip'
          self.archive_path = input_path[4:input_path.find('!')]
          self.file_path = input_path[input_path.find('!') + 2:]
        elif input_path[:1] == "#":
          self.file_type = 'embedded'
          self.file_path = input_path[1:]
        elif input_path[:7] == "http://":
          self.file_type = 'http'
          self.file_path = input_path
        else:
          self.file_path = input_path

        if input_path[:7] != "http://":
          if constants.PLATFORM == 'win32':
            self.archive_path = self.archive_path.replace('/', '\\')
            self.file_path = self.file_path.replace('/', '\\')
          else:
            self.archive_path = self.archive_path.replace('\\', '/')
            self.file_path = self.file_path.replace('\\', '/')

# function to retrieve text value from element without throwing exception
def get_element_text(element_tree, element):
    try:
      text_value = escape(element_tree.find(element).text)
      if text_value is None:
        text_value = ''
    except:
      text_value = ''
    return text_value

