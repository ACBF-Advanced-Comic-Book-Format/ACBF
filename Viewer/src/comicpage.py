# -*- coding: utf-8 -*-
"""comicpage.py - Comic page object and image manipulation methods.

Copyright (C) 2011-2018 Robert Kubik
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


from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance, ImageChops
from xml.sax.saxutils import unescape
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import math
import io
import re

try:
  from . import acbfdocument
  from . import constants
except Exception:
  import acbfdocument
  import constants

class ComicPage():
    
    def __init__(self, window):
        self._window = window
        self.bg_color = '#000000'
        self.rotation = 0
        self.PILBackgroundImage, self.bg_color = self._window.acbf_document.load_page_image(self._window.page_number)
        self.PILBackgroundImageProcessed = None
        self.text_areas = self.references = []
        self.updated = False
        self.frames_total = 0
        self.normal_font = self.emphasis_font = self.strong_font = self.code_font = self.commentary_font = self.sign_font = self.formal_font = self.heading_font = self.letter_font = self.audio_font = self.thought_font = constants.FONTS_LIST[0][1]
        for font in constants.FONTS_LIST:
          if font[0] == self._window.preferences.get_value("normal_font"):
            self.normal_font = font[1]
          if font[0] == self._window.preferences.get_value("emphasis_font"):
            self.emphasis_font = font[1]
          if font[0] == self._window.preferences.get_value("strong_font"):
            self.strong_font = font[1]
          if font[0] == self._window.preferences.get_value("code_font"):
            self.code_font = font[1]
          if font[0] == self._window.preferences.get_value("commentary_font"):
            self.commentary_font = font[1]
        if self._window.acbf_document.font_styles['normal'] != '':
          self.normal_font = self._window.acbf_document.font_styles['normal']
        if self._window.acbf_document.font_styles['emphasis'] != '':
          self.emphasis_font = self._window.acbf_document.font_styles['emphasis']
        if self._window.acbf_document.font_styles['strong'] != '':
          self.strong_font = self._window.acbf_document.font_styles['strong']
        if self._window.acbf_document.font_styles['code'] != '':
          self.code_font = self._window.acbf_document.font_styles['code']
        if self._window.acbf_document.font_styles['commentary'] != '':
          self.commentary_font = self._window.acbf_document.font_styles['commentary']
        if self._window.acbf_document.font_styles['sign'] != '':
          self.sign_font = self._window.acbf_document.font_styles['sign']
        if self._window.acbf_document.font_styles['formal'] != '':
          self.formal_font = self._window.acbf_document.font_styles['formal']
        if self._window.acbf_document.font_styles['heading'] != '':
          self.heading_font = self._window.acbf_document.font_styles['heading']
        if self._window.acbf_document.font_styles['letter'] != '':
          self.letter_font = self._window.acbf_document.font_styles['letter']
        if self._window.acbf_document.font_styles['audio'] != '':
          self.audio_font = self._window.acbf_document.font_styles['audio']
        if self._window.acbf_document.font_styles['thought'] != '':
          self.thought_font = self._window.acbf_document.font_styles['thought']
        if self._window.acbf_document.valid:
          if self._window.acbf_document.font_colors['speech'] == '':
            self.font_color_default = self._window.preferences.get_value("font_color_default")
          else:
            self.font_color_default = self._window.acbf_document.font_colors['speech']
          if len(self.font_color_default) == 13:
            self.font_color_default = '#' + self.font_color_default[1:3] + self.font_color_default[5:7] + self.font_color_default[9:11]
          if self._window.acbf_document.font_colors['inverted'] == '':
            self.font_color_inverted = self._window.preferences.get_value("font_color_inverted")
          else:
            self.font_color_inverted = self._window.acbf_document.font_colors['inverted']
          if len(self.font_color_inverted) == 13:
            self.font_color_inverted = '#' + self.font_color_inverted[1:3] + self.font_color_inverted[5:7] + self.font_color_inverted[9:11]
        else:
          self.font_color_default = self._window.preferences.get_value("font_color_default")
          self.font_color_inverted = self._window.preferences.get_value("font_color_inverted")
        if self._window.acbf_document.languages[self._window.toolbar.language.get_active()][1] == 'TRUE':
          self.draw_text_layer()
        if self._window.acbf_document.valid:
          self.frames = self._window.acbf_document.load_page_frames(self._window.page_number)
          self.frames_total = len(self.frames)

    def update(self, *args):
        self.PILBackgroundImage, self.bg_color = self._window.acbf_document.load_page_image(self._window.page_number)
        if self.bg_color is None:
          self.bg_color = self._window.acbf_document.bg_color
        self.frames = self._window.acbf_document.load_page_frames(self._window.page_number)
        self.frames_total = len(self.frames)
        if self._window.acbf_document.valid and len(self._window.acbf_document.languages) > 0:
          self.text_areas, self.references = self._window.acbf_document.load_page_texts(self._window.page_number, self._window.acbf_document.languages[self._window.toolbar.language.get_active()][0])
        self.updated = False
        for font in constants.FONTS_LIST:
          if font[0] == self._window.preferences.get_value("normal_font"):
            self.normal_font = font[1]
          if font[0] == self._window.preferences.get_value("emphasis_font"):
            self.emphasis_font = font[1]
          if font[0] == self._window.preferences.get_value("strong_font"):
            self.strong_font = font[1]
          if font[0] == self._window.preferences.get_value("code_font"):
            self.code_font = font[1]
          if font[0] == self._window.preferences.get_value("commentary_font"):
            self.commentary_font = font[1]
        if self._window.acbf_document.font_styles['normal'] != '':
          self.normal_font = self._window.acbf_document.font_styles['normal']
        if self._window.acbf_document.font_styles['emphasis'] != '':
          self.emphasis_font = self._window.acbf_document.font_styles['emphasis']
        if self._window.acbf_document.font_styles['strong'] != '':
          self.strong_font = self._window.acbf_document.font_styles['strong']
        if self._window.acbf_document.font_styles['code'] != '':
          self.code_font = self._window.acbf_document.font_styles['code']
        if self._window.acbf_document.font_styles['commentary'] != '':
          self.commentary_font = self._window.acbf_document.font_styles['commentary']
        if self._window.acbf_document.font_styles['sign'] != '':
          self.sign_font = self._window.acbf_document.font_styles['sign']
        if self._window.acbf_document.font_styles['formal'] != '':
          self.formal_font = self._window.acbf_document.font_styles['formal']
        if self._window.acbf_document.font_styles['heading'] != '':
          self.heading_font = self._window.acbf_document.font_styles['heading']
        if self._window.acbf_document.font_styles['letter'] != '':
          self.letter_font = self._window.acbf_document.font_styles['letter']
        if self._window.acbf_document.font_styles['audio'] != '':
          self.audio_font = self._window.acbf_document.font_styles['audio']
        if self._window.acbf_document.font_styles['thought'] != '':
          self.thought_font = self._window.acbf_document.font_styles['thought']
        if self._window.acbf_document.valid:
          if self._window.acbf_document.font_colors['speech'] == '':
            self.font_color_default = self._window.preferences.get_value("font_color_default")
            self._window.acbf_document.font_colors['speech'] = self.font_color_default
          else:
            self.font_color_default = self._window.acbf_document.font_colors['speech']
          if len(self.font_color_default) == 13:
            self.font_color_default = '#' + self.font_color_default[1:3] + self.font_color_default[5:7] + self.font_color_default[9:11]
          if self._window.acbf_document.font_colors['inverted'] == '':
            self.font_color_inverted = self._window.preferences.get_value("font_color_inverted")
          else:
            self.font_color_inverted = self._window.acbf_document.font_colors['inverted']
          if len(self.font_color_inverted) == 13:
            self.font_color_inverted = '#' + self.font_color_inverted[1:3] + self.font_color_inverted[5:7] + self.font_color_inverted[9:11]
        else:
          self.font_color_default = self._window.preferences.get_value("font_color_default")
          self.font_color_inverted = self._window.preferences.get_value("font_color_inverted")
        if self._window.acbf_document.languages[self._window.toolbar.language.get_active()][1] == 'TRUE':
          self.draw_text_layer()
        

    def load_font(self, font, height):
        if font == 'normal':
          if self.normal_font != '':
            return ImageFont.truetype(self.normal_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'emphasis':
          if self.emphasis_font != '':
            return ImageFont.truetype(self.emphasis_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'strong':
          if self.strong_font != '':
            return ImageFont.truetype(self.strong_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'code':
          if self.code_font != '':
            return ImageFont.truetype(self.code_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'commentary':
          if self.commentary_font != '':
            return ImageFont.truetype(self.commentary_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'sign':
          if self.sign_font != '':
            return ImageFont.truetype(self.sign_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'formal':
          if self.formal_font != '':
            return ImageFont.truetype(self.formal_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'heading':
          if self.heading_font != '':
            return ImageFont.truetype(self.heading_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'letter':
          if self.letter_font != '':
            return ImageFont.truetype(self.letter_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'audio':
          if self.audio_font != '':
            return ImageFont.truetype(self.audio_font, height)
          else:
            return ImageFont.load_default()
        elif font == 'thought':
          if self.thought_font != '':
            return ImageFont.truetype(self.thought_font, height)
          else:
            return ImageFont.load_default()

    def remove_xml_tags(self, in_string):
        return unescape(re.sub("<[^>]*>", '', in_string))

    def median(self, lst):
        lst = sorted(lst)
        if len(lst) < 1:
          return None
        if len(lst) %2 == 1:
          return lst[int(((len(lst)+1)/2)-1)]
        else:
          return int(round(float(sum(lst[int(len(lst)/2)-1:int(len(lst)/2)+1]))/2.0, 0))

    def draw_text_layer(self, *args):
        text_areas_draw = []
        if self.PILBackgroundImage.mode != 'RGB':
          self.PILBackgroundImage = self.PILBackgroundImage.convert('RGB')
        image_draw = ImageDraw.Draw(self.PILBackgroundImage)
        for text_area in self.text_areas:
          polygon = []

          if text_area[3] == 0:
            draw = image_draw
            polygon = text_area[0]
          else: # text-area has text-rotation attribute
            polygon = text_area[0]
            original_polygon_boundaries = get_frame_span(text_area[0])
            original_polygon_size = ((original_polygon_boundaries[2] - original_polygon_boundaries[0]), (original_polygon_boundaries[3] - original_polygon_boundaries[1]))

            # move polygon to 0,0
            polygon_center_x = ((original_polygon_boundaries[2] - original_polygon_boundaries[0]) / 2) + original_polygon_boundaries[0]
            polygon_center_y = ((original_polygon_boundaries[3] - original_polygon_boundaries[1]) / 2) + original_polygon_boundaries[1]
            moved_polygon = []
            for point in polygon:
              moved_polygon.append((point[0] - polygon_center_x, point[1] - polygon_center_y))
            
            # rotate polygon
            rotated_polygon = rotatePolygon(moved_polygon, text_area[3])

            # move polygon to image center
            polygon = []
            rotated_polygon_boundaries = get_frame_span(rotated_polygon)
            rotated_polygon_size = ((rotated_polygon_boundaries[2] - rotated_polygon_boundaries[0]), (rotated_polygon_boundaries[3] - rotated_polygon_boundaries[1]))
            for point in rotated_polygon:
              polygon.append((point[0] + rotated_polygon_size[0] / 2, point[1] + rotated_polygon_size[1] / 2))

            # create new image from polygon size
            draw_image = Image.new('RGBA', (rotated_polygon_boundaries[2] - rotated_polygon_boundaries[0], rotated_polygon_boundaries[3] - rotated_polygon_boundaries[1]))
            draw = ImageDraw.Draw(draw_image)

          polygon_boundaries = get_frame_span(polygon)

          # draw text-area background
          if not text_area[6]:
            draw.polygon(polygon, fill=text_area[2])
          
          # calculate some default values
          polygon_area = area(polygon)
          text = text_area[1]
          if '<COMMENTARY>' in text.upper() or text_area[4].upper() == 'COMMENTARY':
            is_commentary = True
          else:
            is_commentary = False
          
          if text_area[4].upper() == 'SIGN':
            is_sign = True
          else:
            is_sign = False

          if text_area[4].upper() == 'FORMAL':
            is_formal = True
          else:
            is_formal = False

          if text_area[4].upper() == 'HEADING':
            is_heading = True
          else:
            is_heading = False

          if text_area[4].upper() == 'LETTER':
            is_letter = True
          else:
            is_letter = False

          if text_area[4].upper() == 'AUDIO':
            is_audio = True
          else:
            is_audio = False

          if text_area[4].upper() == 'THOUGHT':
            is_thought = True
          else:
            is_thought = False

          if text_area[4].upper() == 'CODE':
            is_code = True
          else:
            is_code = False
          
          is_emphasis = is_strong = False
          words = text.replace('a href', 'a_href').replace(' ', ' ˇ').split('ˇ')
          words_upper = text.replace(' ', 'ˇ').upper().split('ˇ')
          area_per_character = polygon_area/len(self.remove_xml_tags(text))
          character_height = int(math.sqrt(area_per_character/2)*2) - 3

          # calculate text drawing start
          polygon_x_min = polygon_boundaries[0]
          polygon_y_min = polygon_boundaries[1]
          polygon_x_max = polygon_boundaries[2]
          polygon_y_max = polygon_boundaries[3]

          text_drawing_start_fits = False
          text_drawing_start = (polygon_x_min + 2, polygon_y_min + 2)

          #draw text
          text_fits = False

          while not text_fits:
              text_fits = True
              character_height = character_height - 1
              space_between_lines = character_height + character_height * 0.3
              
              font = self.load_font('normal', character_height)
              n_font = self.load_font('normal', character_height)
              e_font = self.load_font('emphasis', character_height)
              s_font = self.load_font('strong', character_height)
              c_font = self.load_font('code', character_height)
              co_font = self.load_font('commentary', character_height)
              si_font = self.load_font('sign', character_height)
              fo_font = self.load_font('formal', character_height)
              he_font = self.load_font('heading', character_height)
              le_font = self.load_font('letter', character_height)
              au_font = self.load_font('audio', character_height)
              th_font = self.load_font('thought', character_height)
              n_font_small = self.load_font('normal', int(character_height/2))
              e_font_small = self.load_font('emphasis', int(character_height/2))
              s_font_small = self.load_font('strong', int(character_height/2))
              c_font_small = self.load_font('code', int(character_height/2))
              co_font_small = self.load_font('commentary', int(character_height/2))
              si_font_small = self.load_font('sign', int(character_height/2))
              fo_font_small = self.load_font('formal', int(character_height/2))
              he_font_small = self.load_font('heading', int(character_height/2))
              le_font_small = self.load_font('letter', int(character_height/2))
              au_font_small = self.load_font('audio', int(character_height/2))
              th_font_small = self.load_font('thought', int(character_height/2))

              use_small_font = False

              drawing_word = 0
              drawing_line = 0
              lines = [] # (first_word_start, line_text, last_word_end)
              current_line = ''
              first_word_start = text_drawing_start
              last_word_end = first_word_start

              #draw line
              while drawing_word < len(words):
                #place first word in line
                first_word_fits = False
                tag_split = words[drawing_word].replace('<', 'ˇ<').split('ˇ')
                chunk_size = 0

                for chunk in tag_split:
                  chunk_upper = chunk.upper()
                  if '<SUP>' in chunk_upper or '<SUB>' in chunk_upper or '<A_HREF' in chunk_upper:
                    use_small_font = True
                  elif '<EMPHASIS>' in chunk_upper:
                    is_emphasis = True
                  elif '<STRONG>' in chunk_upper:
                    is_strong = True
                  elif '<CODE>' in chunk_upper or text_area[4].upper() == 'CODE':
                    is_code = True

                  if is_commentary:
                    if use_small_font:
                      font = co_font_small
                    else:
                      font = co_font

                  if is_sign:
                    if use_small_font:
                      font = si_font_small
                    else:
                      font = si_font

                  if is_formal:
                    if use_small_font:
                      font = fo_font_small
                    else:
                      font = fo_font

                  if is_heading:
                    if use_small_font:
                      font = he_font_small
                    else:
                      font = he_font

                  if is_letter:
                    if use_small_font:
                      font = le_font_small
                    else:
                      font = le_font

                  if is_audio:
                    if use_small_font:
                      font = au_font_small
                    else:
                      font = au_font

                  if is_thought:
                    if use_small_font:
                      font = th_font_small
                    else:
                      font = th_font

                  if is_code:
                    if use_small_font:
                      font = c_font_small
                    else:
                      font = c_font

                  if is_emphasis:
                    if use_small_font:
                      font = e_font_small
                    else:
                      font = e_font
                  elif is_strong:
                    if use_small_font:
                      font = s_font_small
                    else:
                      font = s_font
                  elif is_code:
                    if use_small_font:
                      font = c_font_small
                    else:
                      font = c_font

                  if '</SUP>' in chunk_upper or '</SUB>' in chunk_upper or '</A>' in chunk_upper:
                    use_small_font = False

                  if '</EMPHASIS>' in chunk_upper:
                    is_emphasis = False
                  elif '</STRONG>' in chunk_upper:
                    is_strong = False
                  elif '</CODE>' in chunk_upper:
                    is_code = False

                  current_chunk = self.remove_xml_tags(chunk)
                  if current_chunk != '':
                    chunk_size = chunk_size + draw.textsize(current_chunk, font=font)[0]
                    font_height = font.getsize(current_chunk)[1]

                text_size = (chunk_size, font_height + 1)
                
                while not first_word_fits:
                  # check if text fits
                  upper_left_corner_fits = point_inside_polygon(first_word_start[0], first_word_start[1], polygon)
                  upper_right_corner_fits = point_inside_polygon(first_word_start[0] + text_size[0], first_word_start[1], polygon)
                  lower_left_corner_fits = point_inside_polygon(first_word_start[0], first_word_start[1] + text_size[1], polygon)
                  lower_right_corner_fits = point_inside_polygon(first_word_start[0] + text_size[0], first_word_start[1] + text_size[1], polygon)

                  if upper_left_corner_fits and upper_right_corner_fits and lower_left_corner_fits and lower_right_corner_fits:
                    first_word_fits = True
                    first_word_start = (first_word_start[0] + 2, first_word_start[1])
                  elif first_word_start[1] + text_size[1] > polygon_y_max:
                    first_word_fits = True
                    first_word_start = text_drawing_start
                    text_fits = False
                  elif first_word_start[0] + text_size[0] > polygon_x_max: # move down
                    first_word_start = (text_drawing_start[0], first_word_start[1] + 2)
                  else: # move right
                    first_word_start = (first_word_start[0] + 2, first_word_start[1])

                current_line = current_line + words[drawing_word]
                current_pointer = (first_word_start[0] + text_size[0], first_word_start[1])
                drawing_word = drawing_word + 1

                #place other words in line that fit
                other_word_fits = True
                while other_word_fits and drawing_word < len(words):
                  tag_split = words[drawing_word].replace('<', 'ˇ<').split('ˇ')
                  chunk_size = 0

                  for chunk in tag_split:
                    chunk_upper = chunk.upper()
                    if '<BR>' in chunk_upper:
                      current_chunk = ''
                      other_word_fits = False
                    if '<SUP>' in chunk_upper or '<SUB>' in chunk_upper or '<A_HREF' in chunk_upper:
                      use_small_font = True
                    elif '<EMPHASIS>' in chunk_upper:
                      is_emphasis = True
                    elif '<STRONG>' in chunk_upper:
                      is_strong = True
                    elif '<CODE>' in chunk_upper or text_area[4].upper() == 'CODE':
                      is_code = True

                    if is_commentary:
                      if use_small_font:
                        font = co_font_small
                      else:
                        font = co_font

                    if is_sign:
                      if use_small_font:
                        font = si_font_small
                      else:
                        font = si_font

                    if is_formal:
                      if use_small_font:
                        font = fo_font_small
                      else:
                        font = fo_font

                    if is_heading:
                      if use_small_font:
                        font = he_font_small
                      else:
                        font = he_font

                    if is_letter:
                      if use_small_font:
                        font = le_font_small
                      else:
                        font = le_font

                    if is_audio:
                      if use_small_font:
                        font = au_font_small
                      else:
                        font = au_font

                    if is_thought:
                      if use_small_font:
                        font = th_font_small
                      else:
                        font = th_font

                    if is_code:
                      if use_small_font:
                        font = c_font_small
                      else:
                        font = c_font

                    if is_emphasis:
                      if use_small_font:
                        font = e_font_small
                      else:
                        font = e_font
                    elif is_strong:
                      if use_small_font:
                        font = s_font_small
                      else:
                        font = s_font
                    elif is_code:
                      if use_small_font:
                        font = c_font_small
                      else:
                        font = c_font

                    if '</SUP>' in chunk_upper or '</SUB>' in chunk_upper or '</A>' in chunk_upper:
                      use_small_font = False

                    if '</EMPHASIS>' in chunk_upper:
                      is_emphasis = False
                    elif '</STRONG>' in chunk_upper:
                      is_strong = False
                    elif '</CODE>' in chunk_upper:
                      is_code = False

                    current_chunk = self.remove_xml_tags(chunk)
                    if current_chunk != '':
                      chunk_size = chunk_size + draw.textsize(current_chunk, font=font)[0]
                      font_height = font.getsize(current_chunk)[1]

                  text_size = (chunk_size, font_height + 1)
                  upper_right_corner_fits = point_inside_polygon(current_pointer[0] + text_size[0], current_pointer[1], polygon)
                  lower_right_corner_fits = point_inside_polygon(current_pointer[0] + text_size[0], current_pointer[1] + text_size[1], polygon)

                  if other_word_fits and upper_right_corner_fits and lower_right_corner_fits:
                    diff_ratio = (get_frame_span(polygon)[3] - (current_pointer[1] + text_size[1])) / float(text_size[1])
                    if drawing_word == len(words) - 1 and diff_ratio > 1.45 and not is_formal and not is_commentary:
                      #print words[drawing_word].encode("ascii","ignore")
                      #print 'word y:', current_pointer[1] + text_size[1], current_pointer[1] + text_size[1]+ text_size[1]
                      #print 'polygon:', get_frame_span(polygon)
                      #print 'diff:', get_frame_span(polygon)[3] - (current_pointer[1] + text_size[1]), diff_ratio
                      other_word_fits = False
                      last_word_end = (current_pointer[0], current_pointer[1] + text_size[1])
                      lines.append((first_word_start, current_line, last_word_end))
                      current_line = ''
                      first_word_start = (polygon_x_min + 2, first_word_start[1] + space_between_lines)
                    else:
                      current_line = current_line + words[drawing_word]
                      #draw.rectangle((current_pointer[0], current_pointer[1], current_pointer[0] + text_size[0], current_pointer[1] + text_size[1]), outline='#ff0000')
                      current_pointer = (current_pointer[0] + text_size[0], current_pointer[1])
                      drawing_word = drawing_word + 1
                  else:
                    other_word_fits = False
                    last_word_end = (current_pointer[0], current_pointer[1] + text_size[1])
                    lines.append((first_word_start, current_line, last_word_end))
                    current_line = ''
                    first_word_start = (polygon_x_min + 2, first_word_start[1] + space_between_lines)

              last_word_end = (current_pointer[0], current_pointer[1] + text_size[1])
              lines.append((first_word_start, current_line, last_word_end))
              
              if character_height < 1:
                text_fits = True


          if '<CODE>' in lines[0][1].upper() or text_area[4].upper() == 'CODE':
            text_areas_draw.append((character_height, lines, 'CODE', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif '<COMMENTARY>' in lines[0][1].upper() or text_area[4].upper() == 'COMMENTARY':
            text_areas_draw.append((character_height, lines, 'COMMENTARY', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif text_area[4].upper() == 'SIGN':
            text_areas_draw.append((character_height, lines, 'SIGN', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif text_area[4].upper() == 'FORMAL':
            text_areas_draw.append((character_height, lines, 'FORMAL', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif text_area[4].upper() == 'HEADING':
            text_areas_draw.append((character_height, lines, 'HEADING', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif text_area[4].upper() == 'LETTER':
            text_areas_draw.append((character_height, lines, 'LETTER', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif text_area[4].upper() == 'AUDIO':
            text_areas_draw.append((character_height, lines, 'AUDIO', text_area[3], text_area[0], text_area[4], text_area[5]))
          elif text_area[4].upper() == 'THOUGHT':
            text_areas_draw.append((character_height, lines, 'THOUGHT', text_area[3], text_area[0], text_area[4], text_area[5]))
          else:
            text_areas_draw.append((character_height, lines, 'SPEECH', text_area[3], text_area[0], text_area[4], text_area[5]))

          # rotate image back to original rotation after text is drawn
          if text_area[3] != 0:
            draw_image = draw_image.rotate(text_area[3], Image.BILINEAR, 1)
            rotated_image_size = draw_image.size
            left = (rotated_image_size[0] - original_polygon_size[0])//2
            upper = (rotated_image_size[1] - original_polygon_size[1])//2
            right = original_polygon_size[0] + left
            lower = original_polygon_size[1] + upper
            draw_image = draw_image.crop((left, upper, right, lower))
            self.PILBackgroundImage.paste(draw_image, (original_polygon_boundaries[0], original_polygon_boundaries[1]), draw_image)

        # prepare draw
        speach_list = []
        commentary_list = []
        code_list = []
        strong_list = []
        sign_list = []
        formal_list = []
        heading_list = []
        letter_list = []
        audio_list = []
        thought_list = []

        text_areas_draw.sort(key=lambda tup: tup[0]) 

        for text_area in text_areas_draw:
          if text_area[2] == 'SPEECH':
            speach_list.append(text_area[0])
          elif text_area[2] == 'COMMENTARY':
            commentary_list.append(text_area[0])
          elif text_area[2] == 'CODE':
            code_list.append(text_area[0])
          elif text_area[2] == 'STRONG':
            strong_list.append(text_area[0])
          elif text_area[2] == 'SIGN':
            sign_list.append(text_area[0])
          elif text_area[2] == 'FORMAL':
            formal_list.append(text_area[0])
          elif text_area[2] == 'HEADING':
            heading_list.append(text_area[0])
          elif text_area[2] == 'LETTER':
            letter_list.append(text_area[0])
          elif text_area[2] == 'AUDIO':
            audio_list.append(text_area[0])
          elif text_area[2] == 'THOUGHT':
            thought_list.append(text_area[0])

        # drawing
        current_character_height = 0
        for text_area in text_areas_draw:
          lines = []

         # create draw
          polygon = []
          if text_area[3] == 0:
            draw = image_draw
            polygon = text_area[4]
          else: # text-area has text-rotation attribute
            polygon = text_area[4]
            original_polygon_boundaries = get_frame_span(text_area[4])
            original_polygon_size = ((original_polygon_boundaries[2] - original_polygon_boundaries[0]), (original_polygon_boundaries[3] - original_polygon_boundaries[1]))

            # move polygon to 0,0
            polygon_center_x = ((original_polygon_boundaries[2] - original_polygon_boundaries[0]) / 2) + original_polygon_boundaries[0]
            polygon_center_y = ((original_polygon_boundaries[3] - original_polygon_boundaries[1]) / 2) + original_polygon_boundaries[1]
            moved_polygon = []
            for point in polygon:
              moved_polygon.append((point[0] - polygon_center_x, point[1] - polygon_center_y))
            
            # rotate polygon
            rotated_polygon = rotatePolygon(moved_polygon, text_area[3])

            # move polygon to image center
            polygon = []
            rotated_polygon_boundaries = get_frame_span(rotated_polygon)
            rotated_polygon_size = ((rotated_polygon_boundaries[2] - rotated_polygon_boundaries[0]), (rotated_polygon_boundaries[3] - rotated_polygon_boundaries[1]))
            for point in rotated_polygon:
              polygon.append((point[0] + rotated_polygon_size[0] / 2, point[1] + rotated_polygon_size[1] / 2))

            # create new image from polygon size
            draw_image = Image.new('RGBA', (rotated_polygon_boundaries[2] - rotated_polygon_boundaries[0], rotated_polygon_boundaries[3] - rotated_polygon_boundaries[1]))
            draw = ImageDraw.Draw(draw_image)

          # normalize text size
          normalized_character_height = text_area[0]
          if text_area[2] == 'SPEACH' and text_area[0] / float(self.median(speach_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'COMMENTARY' and text_area[0] / float(self.median(commentary_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'CODE' and text_area[0] / float(self.median(code_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'SIGN' and text_area[0] / float(self.median(sign_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'FORMAL' and text_area[0] / float(self.median(formal_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'HEADING' and text_area[0] / float(self.median(heading_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'LETTER' and text_area[0] / float(self.median(letter_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'AUDIO' and text_area[0] / float(self.median(audio_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))
          elif text_area[2] == 'THOUGHT' and text_area[0] / float(self.median(thought_list)) > 1.1:
            normalized_character_height = int(round(text_area[0] / 1.1, 0))

          # load fonts
          if current_character_height != normalized_character_height:
            current_character_height = normalized_character_height
            font = self.load_font('normal', current_character_height)
            n_font = self.load_font('normal', current_character_height)
            e_font = self.load_font('emphasis', current_character_height)
            s_font = self.load_font('strong', current_character_height)
            c_font = self.load_font('code', current_character_height)
            co_font = self.load_font('commentary', current_character_height)
            si_font = self.load_font('sign', current_character_height)
            fo_font = self.load_font('formal', current_character_height)
            he_font = self.load_font('heading', current_character_height)
            le_font = self.load_font('letter', current_character_height)
            au_font = self.load_font('audio', current_character_height)
            th_font = self.load_font('thought', current_character_height)
            n_font_small = self.load_font('normal', int(current_character_height/2))
            e_font_small = self.load_font('emphasis', int(current_character_height/2))
            s_font_small = self.load_font('strong', int(current_character_height/2))
            c_font_small = self.load_font('code', int(current_character_height/2))
            co_font_small = self.load_font('commentary', int(current_character_height/2))
            si_font_small = self.load_font('sign', int(current_character_height/2))
            fo_font_small = self.load_font('formal', int(current_character_height/2))
            he_font_small = self.load_font('heading', int(current_character_height/2))
            le_font_small = self.load_font('letter', int(current_character_height/2))
            au_font_small = self.load_font('audio', int(current_character_height/2))
            th_font_small = self.load_font('thought', int(current_character_height/2))

          # calculate new line length
          if normalized_character_height != text_area[0]:
            #print "normalized", text_area[0], normalized_character_height, text_area[1]
            for line in text_area[1]:
              # calculate some default values
              text = line[1]
              if '<COMMENTARY>' in text.upper() or text_area[2] == 'COMMENTARY':
                is_commentary = True
              else:
                is_commentary = False

              if text_area[2] == 'SIGN':
                is_sign = True
              else:
                is_sign = False

              if text_area[2] == 'FORMAL':
                is_formal = True
              else:
                is_formal = False

              if text_area[2] == 'HEADING':
                is_heading = True
              else:
                is_heading = False

              if text_area[2] == 'LETTER':
                is_letter = True
              else:
                is_letter = False

              if text_area[2] == 'AUDIO':
                is_audio = True
              else:
                is_audio = False

              if text_area[2] == 'THOUGHT':
                is_thought = True
              else:
                is_thought = False

              if text_area[2] == 'CODE':
                is_code = True
              else:
                is_code = False
              
              is_emphasis = is_strong = False
              words = text.replace('a href', 'a_href').replace(' ', ' ˇ').split('ˇ')
              words_upper = text.replace(' ', 'ˇ').upper().split('ˇ')
              drawing_word = 0
              line_length = 0

              while drawing_word < len(words):
                tag_split = words[drawing_word].replace('<', 'ˇ<').split('ˇ')
                chunk_size = 0

                for chunk in tag_split:
                  chunk_upper = chunk.upper()
                  if '<BR>' in chunk_upper:
                    current_chunk = ''
                  if '<SUP>' in chunk_upper or '<SUB>' in chunk_upper or '<A_HREF' in chunk_upper:
                    use_small_font = True
                  elif '<EMPHASIS>' in chunk_upper:
                    is_emphasis = True
                  elif '<STRONG>' in chunk_upper:
                    is_strong = True
                  elif '<CODE>' in chunk_upper:
                    is_code = True

                  if is_commentary:
                    if use_small_font:
                      font = co_font_small
                    else:
                      font = co_font

                  if is_sign:
                    if use_small_font:
                      font = si_font_small
                    else:
                      font = si_font

                  if is_formal:
                    if use_small_font:
                      font = fo_font_small
                    else:
                      font = fo_font

                  if is_heading:
                    if use_small_font:
                      font = he_font_small
                    else:
                      font = he_font

                  if is_letter:
                    if use_small_font:
                      font = le_font_small
                    else:
                      font = le_font

                  if is_audio:
                    if use_small_font:
                      font = au_font_small
                    else:
                      font = au_font

                  if is_thought:
                    if use_small_font:
                      font = th_font_small
                    else:
                      font = th_font

                  if is_code:
                    if use_small_font:
                      font = c_font_small
                    else:
                      font = c_font

                  if is_emphasis:
                    if use_small_font:
                      font = e_font_small
                    else:
                      font = e_font
                  elif is_strong:
                    if use_small_font:
                      font = s_font_small
                    else:
                      font = s_font
                  elif is_code:
                    if use_small_font:
                      font = c_font_small
                    else:
                      font = c_font

                  if '</SUP>' in chunk_upper or '</SUB>' in chunk_upper or '</A>' in chunk_upper:
                    use_small_font = False

                  if '</EMPHASIS>' in chunk_upper:
                    is_emphasis = False
                  elif '</STRONG>' in chunk_upper:
                    is_strong = False
                  elif '</CODE>' in chunk_upper:
                    is_code = False

                  current_chunk = self.remove_xml_tags(chunk)
                  if current_chunk != '':
                    chunk_size = chunk_size + draw.textsize(current_chunk, font=font)[0]
                drawing_word = drawing_word + 1
                line_length = line_length + chunk_size
              change_in_height = int(round((((line[2][1] - line[0][1]) - (current_character_height + 1)) / 2), 0))
              lines.append(((line[0][0], line[0][1] - change_in_height), line[1], (line[0][0] + line_length, line[0][1] + current_character_height + 1 - change_in_height)))
          else:
            for line in text_area[1]:
              lines.append((line[0], line[1], line[2]))

          #vertical bubble alignment
          if len(lines) > 0 and text_area[2] != 'FORMAL':
            points = []
            for line in lines:
              points.append((line[0][0], line[0][1]))
              points.append((line[2][0], line[2][1]))
            vertical_move =  int(((get_frame_span(polygon)[3] - get_frame_span(points)[3]) - (get_frame_span(points)[1] - get_frame_span(polygon)[1]))/2)
            #print get_frame_span(points), get_frame_span(polygon), vertical_move
            #draw.rectangle((get_frame_span(polygon)[0], get_frame_span(polygon)[1], get_frame_span(polygon)[2], get_frame_span(polygon)[3]), outline="#FF0000")
            #draw.rectangle((get_frame_span(points)[0], get_frame_span(points)[1], get_frame_span(points)[2], get_frame_span(points)[3]), outline="#FFFF00")
            #draw.polygon(polygon, outline="#000000")

            if vertical_move > 0:
              #check if inside
              is_inside = True
              for move in range(vertical_move, 1, -1):
                is_inside = True
                for line in lines:
                  if not point_inside_polygon(line[0][0], line[0][1] + move + int(current_character_height / 5), polygon):
                    is_inside = False
                  elif not point_inside_polygon(line[2][0], line[2][1] + move + int(current_character_height / 5), polygon):
                    #draw.rectangle((line[0][0], line[0][1], line[2][0], line[2][1] + move), outline="#FFFFFF")
                    is_inside = False
                if is_inside:
                  vertical_move = move
                  break

              if is_inside:
                #print "move", vertical_move, lines[0]
                for idx, line in enumerate(lines):
                  #lines[idx] = ((line[0][0], line[0][1] + vertical_move), line[1], (line[2][0], line[2][1] + vertical_move))
                  #draw.rectangle((line[0][0], line[0][1] + vertical_move, line[2][0], line[2][1] + vertical_move), outline="#FFFFFF")

                  #realign to left
                  min_coordinate_set = False
                  current_coordinate = line[0][0]
                  min_coordinate = line[0][0] - 2
                  while min_coordinate_set == False:
                    if (point_inside_polygon(current_coordinate, line[0][1] + int(current_character_height/2), polygon) and
                        point_inside_polygon(current_coordinate, line[2][1], polygon)):
                      min_coordinate = current_coordinate
                    else:
                      min_coordinate_set = True
                    current_coordinate = current_coordinate - 2
                  lines[idx] = ((min_coordinate + 2, line[0][1] + vertical_move - 1), line[1], (line[2][0] - (line[0][0] - min_coordinate), line[2][1] + vertical_move - 1))
                  #draw.rectangle((min_coordinate + 2, line[0][1] + vertical_move, line[2][0] - (line[0][0] - min_coordinate), line[2][1] + vertical_move), outline="#FF0000")


          if '<COMMENTARY>' in lines[0][1].upper() or text_area[2] == 'COMMENTARY':
            is_commentary = True
          else:
            is_commentary = False

          if text_area[2] == 'SIGN':
            is_sign = True
          else:
            is_sign = False

          if text_area[2] == 'FORMAL':
            is_formal = True
          else:
            is_formal = False

          if text_area[2] == 'HEADING':
            is_heading = True
          else:
            is_heading = False

          if text_area[2] == 'LETTER':
            is_letter = True
          else:
            is_letter = False

          if text_area[2] == 'AUDIO':
            is_audio = True
          else:
            is_audio = False

          if text_area[2] == 'THOUGHT':
            is_thought = True
          else:
            is_thought = False

          if text_area[2] == 'CODE':
            is_code = True
          else:
            is_code = False

          #drawing
          font = n_font
          font_small = n_font_small
          font_color = self.font_color_default
          strikethrough_word = False
          use_small_font = False
          use_superscript = False
          use_subscript = False

          if is_commentary:
            font = co_font
            font_small = co_font_small
            font_color = self._window.acbf_document.font_colors['commentary']
          elif is_sign:
            font = si_font
            font_small = si_font_small
            font_color = self._window.acbf_document.font_colors['sign']
          elif is_formal:
            font = fo_font
            font_small = fo_font_small
            font_color = self._window.acbf_document.font_colors['formal']
          elif is_heading:
            font = he_font
            font_small = he_font_small
            font_color = self._window.acbf_document.font_colors['heading']
          elif is_letter:
            font = le_font
            font_small = le_font_small
            font_color = self._window.acbf_document.font_colors['letter']
          elif is_audio:
            font = au_font
            font_small = au_font_small
            font_color = self._window.acbf_document.font_colors['audio']
          elif is_thought:
            font = th_font
            font_small = th_font_small
            font_color = self._window.acbf_document.font_colors['thought']
          elif is_code:
            font = c_font
            font_small = c_font_small
            font_color = self._window.acbf_document.font_colors['code']

          # idetify last line in paragraph
          for idx, line in enumerate(lines):
            if '<BR>' in line[1]:
              lines[idx] = (line[0], line[1].replace('<BR>', ''), line[2])
              lines[idx-1] = (lines[idx-1][0], '<BR>' + lines[idx-1][1], lines[idx-1][2])
          
          for idx, line in enumerate(lines):
            is_last_line = False
            old_line = ''
            current_pointer = line[0]
            #draw.rectangle((line[0][0], line[0][1], line[2][0], line[2][1]), outline="#FFFFFF")
            max_coordinate_set = False
            max_coordinate = line[2][0]
            current_coordinate = line[2][0]

            # get max line length
            while max_coordinate_set == False:
              if (point_inside_polygon(current_coordinate, current_pointer[1] + int(current_character_height/2), polygon) and
                  point_inside_polygon(current_coordinate, line[2][1], polygon)):
                max_coordinate = current_coordinate
              else:
                max_coordinate_set = True
              current_coordinate = current_coordinate + 2

            # split by tags
            tag_split = line[1].split('<')
            for i in range(len(tag_split)):
              if i > 0:
                tag_split[i] = '<' + tag_split[i]

            for chunk in tag_split:
              chunk_upper = chunk.upper()

              if '<BR>' in chunk_upper:
                is_last_line = True

              if '<INVERTED>' in chunk_upper or text_area[6]:
                font_color = self.font_color_inverted
                text_area = (text_area[0], text_area[1], text_area[2], text_area[3], text_area[4], text_area[5], True)
              elif '</INVERTED>' in chunk_upper:
                font_color = self._window.acbf_document.font_colors[text_area[2].lower()]
              elif not text_area[6]:
                font_color = self._window.acbf_document.font_colors[text_area[2].lower()]

              if '<EMPHASIS>' in chunk_upper:
                font = e_font
                font_small = e_font_small
              elif '<STRONG>' in chunk_upper:
                font = s_font
                font_small = s_font_small
              elif '<CODE>' in chunk_upper:
                font = c_font
                font_small = c_font_small
              elif '<STRIKETHROUGH>' in chunk_upper:
                strikethrough_word = True
              elif '</EMPHASIS>' in chunk_upper or '</STRONG>' in chunk_upper or '</CODE>' in chunk_upper:
                if is_commentary:
                  font = co_font
                  font_small = co_font_small
                elif is_sign:
                  font = si_font
                  font_small = si_font_small
                elif is_formal:
                  font = fo_font
                  font_small = fo_font_small
                elif is_heading:
                  font = he_font
                  font_small = he_font_small
                elif is_letter:
                  font = le_font
                  font_small = le_font_small
                elif is_audio:
                  font = au_font
                  font_small = au_font_small
                elif is_thought:
                  font = th_font
                  font_small = th_font_small
                elif is_code:
                  font = c_font
                  font_small = c_font_small
                else:
                  font = n_font
                  font_small = n_font_small
              elif '</STRIKETHROUGH>' in chunk_upper:
                strikethrough_word = False
              elif '</SUP>' in chunk_upper:
                use_superscript = False
                use_small_font = False
              elif '</SUB>' in chunk_upper:
                use_subscript = False
                use_small_font = False
              elif '</A>' in chunk_upper:
                use_small_font = False
              elif '<SUP>' in chunk_upper or '<A_HREF' in chunk_upper:
                use_small_font = True
                use_superscript = True
              elif '<SUB>' in chunk_upper:
                use_small_font = True
                use_subscript = True

              if len(font_color) == 13:
                font_color = '#' + font_color[1:3] + font_color[5:7] + font_color[9:11]
              
              current_word = self.remove_xml_tags(chunk)
              if current_word == '':
                continue

              # align the text
              if old_line != line:
                justify_space = 0
                if is_commentary or (text_area[5].upper() == 'FORMAL' and idx + 1 == len(lines)): #left align
                  space_between_words = draw.textsize(' ', font=font)[0]
                elif text_area[5].upper() == 'FORMAL': #justify
                  w_count = len(line[1].strip().split(' ')) - 1
                  if is_last_line:
                    justify_space = 0
                  elif w_count > 0:
                    justify_space = (max_coordinate - line[2][0]) / w_count
                  else:
                    justify_space = 0
                  space_between_words = draw.textsize(' ', font=font)[0] + justify_space
                else: #center
                  space_between_words = draw.textsize('n n', font=font)[0] - draw.textsize('nn', font=font)[0]
                  line_length = line[2][0] - line[0][0]
                  mid_bubble_x = ((get_frame_span(text_area[4])[0] + get_frame_span(text_area[4])[2]) / 2) - line_length / 2
                  max_coordinate_x = current_pointer[0] + int((max_coordinate - line[2][0])/2)
                  #draw.rectangle((get_frame_span(text_area[4])), outline="#FF0000")
                  #draw.rectangle((current_pointer[0], current_pointer[1], current_pointer[0] + line_length, current_pointer[1] + int(current_character_height)), outline="#FF0000")
                  #draw.rectangle((mid_bubble_x, current_pointer[1], mid_bubble_x + line_length, current_pointer[1] + int(current_character_height)), outline="#00FF00")
                  #print line, mid_bubble_x, line[0][0], max_coordinate - line_length, max_coordinate_x
                  if text_area[3] != 0:
                    current_pointer = (max_coordinate_x, current_pointer[1])
                  elif mid_bubble_x >= line[0][0] and mid_bubble_x <= max_coordinate - line_length:
                    current_pointer = (mid_bubble_x, current_pointer[1])
                  elif mid_bubble_x > max_coordinate - line_length:
                    current_pointer = (max_coordinate - line_length, current_pointer[1])
                  elif mid_bubble_x < line[0][0]:
                    current_pointer = (line[0][0], current_pointer[1])
                  else:
                    current_pointer = (max_coordinate_x, current_pointer[1])
                old_line = line
            
              #length = line[2][0] - line[0][0]
              #draw.rectangle((current_pointer[0], current_pointer[1], current_pointer[0] + length, current_pointer[1] + int(current_character_height)), outline="#0000FF")

              if use_small_font and current_word != '':
                if use_subscript:
                  current_pointer = (current_pointer[0], current_pointer[1] + int(current_character_height * 0.7))
                  draw.text(current_pointer, current_word, font=font_small, fill=font_color)
                  current_pointer = (current_pointer[0], current_pointer[1] - int(current_character_height * 0.7))
                elif use_superscript:
                  draw.text(current_pointer, current_word, font=font_small, fill=font_color)
                  #draw.rectangle((current_pointer[0] - 1, current_pointer[1] - 1, current_pointer[0] + draw.textsize(current_word, font=font_small)[0] + 1, current_pointer[1] + int(character_height * 0.7) + 1), outline=font_color)
                  if '<A_HREF' in chunk_upper:
                    reference_id = re.sub("[^#]*#", '', chunk)
                    reference_id = re.sub("\".*", '', reference_id)
                    for idxr, reference in enumerate(self.references):
                      if reference_id == reference[0]:
                        rectangle = [(current_pointer[0] - 5, current_pointer[1] - 5),
                                     (current_pointer[0] + draw.textsize(current_word, font=font_small)[0] + 5, current_pointer[1] - 5),
                                     (current_pointer[0] + draw.textsize(current_word, font=font_small)[0] + 5, current_pointer[1] + int(current_character_height * 0.7) + 5),
                                     (current_pointer[0] - 5, current_pointer[1] + int(current_character_height * 0.7) + 5)]
                        self.references[idxr] = (reference[0], reference[1], rectangle)
            
                text_size = (draw.textsize(current_word, font=font_small)[0], int(current_character_height * 0.5))
                strikethrough_rectangle = [current_pointer[0] - int(space_between_words/2),
                                           current_pointer[1] + int(current_character_height/2) + 1,
                                           current_pointer[0] + text_size[0] + int(space_between_words/2),
                                           current_pointer[1] + int(current_character_height/2) + 1 - int(current_character_height/10)]

                current_pointer = (current_pointer[0] + text_size[0], current_pointer[1])

              else:
                word_start = current_pointer
                text_size = [0, current_character_height]
                word_count = len(current_word.strip().split(' '))
                line_length_total = draw.textsize(current_word.strip(), font=font)[0]
                word_length_total = 0
                for one_word in current_word.split(' '):
                  word_length_total = word_length_total + draw.textsize(one_word.strip(), font=font)[0]

                space_length = line_length_total - word_length_total
                if word_count > 1:
                  one_space = float(space_length/float(word_count - 1))
                elif space_length > 0:
                  one_space = space_length
                else:
                  one_space = draw.textsize(current_word + ' M', font=font)[0] - draw.textsize(current_word + 'M', font=font)[0]

                #print '#' + current_word.encode('ascii', 'ignore') + '#', line_length_total, word_length_total, space_length, one_space
                
                for one_word in current_word.split(' '):
                  if one_word == '':
                    continue
                  if one_word[0].upper() == 'J' and text_area[5].upper() != 'FORMAL': #dirty fix
                    current_pointer = (current_pointer[0] + 1, current_pointer[1])
                  elif font == e_font or font == s_font:
                    current_pointer = (current_pointer[0] - 1, current_pointer[1])
                  draw.text(current_pointer, one_word + ' ', font=font, fill=font_color)
                  word_length = max(draw.textsize(one_word.strip(), font=font)[0] + one_space, draw.textsize(one_word.strip() + ' ', font=font)[0])
                  if text_area[5].upper() == 'FORMAL':
                    word_length = word_length + justify_space
                  text_size = (text_size[0] + word_length, current_character_height)
                  current_pointer = (current_pointer[0] + word_length, current_pointer[1])
                  if one_word[-1].upper() == 'J' and text_area[5].upper() != 'FORMAL': #dirty fix:
                    current_pointer = (current_pointer[0] + 1, current_pointer[1])
                  elif font == e_font or font == s_font:
                    current_pointer = (current_pointer[0] + 1, current_pointer[1])
                  
                #draw.text(current_pointer, current_word, font=font, fill=font_color)
                #text_size = (draw.textsize(current_word, font=font)[0], current_character_height)
                #current_pointer = (current_pointer[0] + text_size[0], current_pointer[1])
                strikethrough_rectangle = [word_start[0] - int(space_between_words/2),
                                           word_start[1] + int(current_character_height/2) + 1,
                                           word_start[0] + line_length_total + int(space_between_words/2),
                                           word_start[1] + int(current_character_height/2) + 1 - int(current_character_height/10)]

              if strikethrough_word:
                draw.rectangle(strikethrough_rectangle, outline=font_color, fill=font_color)

          # rotate image back to original rotation after text is drawn
          if text_area[3] != 0:
            draw_image = draw_image.rotate(text_area[3], Image.BILINEAR, 1)
            rotated_image_size = draw_image.size
            left = (rotated_image_size[0] - original_polygon_size[0])//2
            upper = (rotated_image_size[1] - original_polygon_size[1])//2
            right = original_polygon_size[0] + left
            lower = original_polygon_size[1] + upper
            draw_image = draw_image.crop((left, upper, right, lower))
            self.PILBackgroundImage.paste(draw_image, (original_polygon_boundaries[0], original_polygon_boundaries[1]), draw_image)

        try:
          del draw
        except:
          None

# Image manipulation
def get_PixBufImage(ComicPageObject, size, zoom_level):
    """Returns final PixBuf image for the main window, its width and height"""
    frame_color = ComicPageObject.bg_color
    try:
      cpPILBackgroundImage = ComicPageObject.PILBackgroundImage.copy()

      # remove borders
      if (ComicPageObject._window.preferences.get_value("crop_border") == "True" and zoom_level == 2):
        bg = Image.new(cpPILBackgroundImage.mode, cpPILBackgroundImage.size, cpPILBackgroundImage.getpixel((0,0)))
        diff = ImageChops.difference(cpPILBackgroundImage, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
          cpPILBackgroundImage = cpPILBackgroundImage.crop(bbox)

          bg = Image.new(cpPILBackgroundImage.mode, cpPILBackgroundImage.size, cpPILBackgroundImage.getpixel((0,0)))
          diff = ImageChops.difference(cpPILBackgroundImage, bg)
          diff = ImageChops.add(diff, diff, 2.0, -100)
          bbox = diff.getbbox()
          if bbox:
            cpPILBackgroundImage = cpPILBackgroundImage.crop(bbox)

      if (zoom_level == 3 and ComicPageObject.frames_total > 0):
        # get frame polygon coordinates and color
        #frame_coordinates = ComicPageObject.frames[ComicPageObject._window.frame_number - 1][0]
        frame_color = ComicPageObject.frames[ComicPageObject._window.frame_number - 1][1]
        if frame_color == None:
           frame_color = ComicPageObject.bg_color

        # create mask based on the frame coordinates
        #image_size = ComicPageObject.PILBackgroundImage.size
        #mask = Image.new('L', image_size, 0)
        #draw = ImageDraw.Draw(mask)
        #draw.polygon(frame_coordinates, fill=255)
        #cpPILBackgroundImage.putalpha(mask)
        #cpPILBackgroundImage = cpPILBackgroundImage.crop(get_frame_span(frame_coordinates))

      if zoom_level == 2:
        if ComicPageObject.rotation in (0, 180):
          wpercent = (size[0]/float(cpPILBackgroundImage.size[0]))
          hsize = int((float(cpPILBackgroundImage.size[1])*float(wpercent)))
          size = (size[0], hsize)
        else:
          hpercent = (size[1]/float(cpPILBackgroundImage.size[0]))
          vsize = int((float(cpPILBackgroundImage.size[1])*float(hpercent)))
          size = (vsize, size[1])

      # calculate image_ratio and drawable_size_ratio
      image_ratio = cpPILBackgroundImage.size[0]/cpPILBackgroundImage.size[1]
      drawable_size_ratio = ComicPageObject._window.drawable_size[0]/ComicPageObject._window.drawable_size[1]

      if image_ratio >= 1:
        image_ratio = 1
      else:
        image_ratio = 0
      
      if drawable_size_ratio >= 1:
        drawable_size_ratio = 1
      else:
        drawable_size_ratio = 0

      # autorotate
      if (ComicPageObject._window.preferences.get_value("autorotate") == "True" and
          zoom_level in (1,3) and
          image_ratio != drawable_size_ratio):
        cpPILBackgroundImage = cpPILBackgroundImage.rotate(90)
      elif ComicPageObject.rotation != 0:
        cpPILBackgroundImage = cpPILBackgroundImage.rotate(ComicPageObject.rotation)

      # resize image
      if ComicPageObject._window.preferences.get_value("image_stretch") == "True" and zoom_level != 3:
        wpercent = (size[0]/float(cpPILBackgroundImage.size[0]))
        hpercent = (size[1]/float(cpPILBackgroundImage.size[1]))
        if cpPILBackgroundImage.size[0] > size[0] and cpPILBackgroundImage.size[1] > size[1]:
          if wpercent > hpercent:
            size = (int((float(cpPILBackgroundImage.size[0])*float(hpercent))), int((float(cpPILBackgroundImage.size[1])*float(hpercent))))
          else:
            size = (int((float(cpPILBackgroundImage.size[0])*float(wpercent))), int((float(cpPILBackgroundImage.size[1])*float(wpercent))))
        elif cpPILBackgroundImage.size[0] > size[0]:
          size = (size[0], int((float(cpPILBackgroundImage.size[1])*float(wpercent))))
        elif cpPILBackgroundImage.size[1] > size[1]:
          size = (int((float(cpPILBackgroundImage.size[0])*float(hpercent))), size[1])
        elif cpPILBackgroundImage.size[0] < size[0] and cpPILBackgroundImage.size[1] < size[1]:
          if wpercent > hpercent:
            size = (int((float(cpPILBackgroundImage.size[0])*float(hpercent))), int((float(cpPILBackgroundImage.size[1])*float(hpercent))))
          else:
            size = (int((float(cpPILBackgroundImage.size[0])*float(wpercent))), int((float(cpPILBackgroundImage.size[1])*float(wpercent))))
        elif cpPILBackgroundImage.size[0] < size[0]:
          size = (int((float(cpPILBackgroundImage.size[0])*float(hpercent))), size[1])
        elif cpPILBackgroundImage.size[1] < size[1]:
          size = (size[0], int((float(cpPILBackgroundImage.size[1])*float(wpercent))))
          
        if ComicPageObject._window.preferences.get_value("image_resize_filter") == "0":
          cpPILBackgroundImage = cpPILBackgroundImage.resize(size, Image.NEAREST)
        elif ComicPageObject._window.preferences.get_value("image_resize_filter") == "1":
          cpPILBackgroundImage = cpPILBackgroundImage.resize(size, Image.BILINEAR)
        elif ComicPageObject._window.preferences.get_value("image_resize_filter") == "2":
          cpPILBackgroundImage = cpPILBackgroundImage.resize(size, Image.BICUBIC)
        else:
          cpPILBackgroundImage = cpPILBackgroundImage.resize(size, Image.ANTIALIAS)
      elif zoom_level != 3:
        if ComicPageObject._window.preferences.get_value("image_resize_filter") == "0":
          cpPILBackgroundImage.thumbnail(size, Image.NEAREST)
        elif ComicPageObject._window.preferences.get_value("image_resize_filter") == "1":
          cpPILBackgroundImage.thumbnail(size, Image.BILINEAR)
        elif ComicPageObject._window.preferences.get_value("image_resize_filter") == "2":
          cpPILBackgroundImage.thumbnail(size, Image.BICUBIC)
        else:
          cpPILBackgroundImage.thumbnail(size, Image.ANTIALIAS)

      # adjust image sharpness
      if int(ComicPageObject._window.image_sharpness_value * 10) != 0 and ComicPageObject._window.sharpness_button_toggle == True:
        cpPILBackgroundImage = ImageEnhance.Sharpness(cpPILBackgroundImage).enhance(ComicPageObject._window.image_sharpness_value + 1)

      # adjust saturation
      if int(ComicPageObject._window.image_saturation_value * 10) != 0 and ComicPageObject._window.saturation_button_toggle == True:
        cpPILBackgroundImage = ImageEnhance.Color(cpPILBackgroundImage).enhance(ComicPageObject._window.image_saturation_value + 1)

      # adjust brightness
      if int(ComicPageObject._window.image_brightness_value * 10) != 0 and ComicPageObject._window.brightness_button_toggle == True:
        cpPILBackgroundImage = ImageEnhance.Brightness(cpPILBackgroundImage).enhance(ComicPageObject._window.image_brightness_value + 1)

      # adjust contrast
      if int(ComicPageObject._window.image_contrast_value * 10) != 0 and ComicPageObject._window.contrast_button_toggle == True:
        cpPILBackgroundImage = ImageEnhance.Contrast(cpPILBackgroundImage).enhance(ComicPageObject._window.image_contrast_value + 1)

      # convert to PixBuf
      PixBufImage = pil_to_pixbuf(cpPILBackgroundImage, frame_color)
      ComicPageObject.updated = True
    except:
      return None, 0, 0, ComicPageObject.bg_color

    ComicPageObject.PILBackgroundImageProcessed = cpPILBackgroundImage.copy()

    return PixBufImage, PixBufImage.get_width(), PixBufImage.get_height(), frame_color

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

def get_frame_span(frame_coordinates):
    """returns x_min, y_min, x_max, y_max coordinates of a frame"""
    x_min = 100000000
    x_max = -1
    y_min = 100000000
    y_max = -1
    for frame_tuple in frame_coordinates:
      if x_min > frame_tuple[0]:
        x_min = frame_tuple[0]
      if y_min > frame_tuple[1]:
        y_min = frame_tuple[1]
      if x_max < frame_tuple[0]:
        x_max = frame_tuple[0]
      if y_max < frame_tuple[1]:
        y_max = frame_tuple[1]
    return (int(x_min), int(y_min), int(x_max), int(y_max))

def point_inside_polygon(x,y,poly):
    n = len(poly)
    inside = False

    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y
    return inside

def area(p):
    return 0.5 * abs(sum(x0*y1 - x1*y0
                         for ((x0, y0), (x1, y1)) in segments(p)))

def segments(p):
    return list(zip(p, p[1:] + [p[0]]))

def rotate_point(x, y, xm, ym, xm2, ym2, a):
    rotation_angle = float(a * math.pi/180)
    x_coord = float(x - xm)
    y_coord = float(y - ym)
    x_coord2 = float(x_coord*math.cos(rotation_angle) - y_coord*math.sin(rotation_angle) + xm2)
    y_coord2 = float(x_coord*math.sin(rotation_angle) + y_coord*math.cos(rotation_angle) + ym2)
    return int(x_coord2), int(y_coord2)

def rotatePolygon(polygon,theta):
    """Rotates the given polygon which consists of corners represented as (x,y),
    around the ORIGIN, clock-wise, theta degrees"""
    theta = math.radians(theta)
    rotatedPolygon = []
    for corner in polygon :
        rotatedPolygon.append(( corner[0]*math.cos(theta)-corner[1]*math.sin(theta) , corner[0]*math.sin(theta)+corner[1]*math.cos(theta)) )
    return rotatedPolygon
