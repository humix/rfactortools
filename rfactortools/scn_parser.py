# rFactor .scn/.gen file manipulation tool
# Copyright (C) 2014 Ingo Ruhnke <grumbel@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
import ntpath
import posixpath

import rfactortools


keyvalue_regex = re.compile(r'^\s*([^=]+)\s*=\s*(.*)\s*')
comment_regex = re.compile(r'(.*?)(//.*)')
section_start_regex = re.compile(r'\s*{')
section_end_regex = re.compile(r'\s*}')


def posix2scn_path(path):
    # minor path cleanup only, not using posixpath.normpath() as that
    # would replace "<TEAMDIR>/.." with ".", not what we want
    path = re.sub(r'/+', r'/', path)
    path = re.sub(r'/$', r'', path)

    path = path.replace(posixpath.sep, ntpath.sep)

    return path


def scn2posix_path(path):
    path = path.replace(ntpath.sep, posixpath.sep)
    path = re.sub(r'<VEHDIR>', r'<VEHDIR>/', path, count=1, flags=re.I)
    path = re.sub(r'<TEAMDIR>', r'<TEAMDIR>/', path, count=1, flags=re.I)

    # minor path cleanup only, not using posixpath.normpath() as that
    # would replace "<TEAMDIR>/.." with ".", not what we want
    path = re.sub(r'/+', r'/', path)
    path = re.sub(r'/$', r'', path)

    return path


def process_scnfile(filename, parser):
    with rfactortools.open_read(filename) as fin:
        for orig_line in fin.read().splitlines():
            line = orig_line

            m = comment_regex.match(line)
            if m:
                comment = m.group(2)
                line = m.group(1)
            else:
                comment = None

            m = keyvalue_regex.match(line)
            m_sec_start = section_start_regex.match(line)
            m_sec_stop = section_end_regex.match(line)
            if m:
                key, value = m.group(1), m.group(2)
                parser.on_key_value(key, value.strip(), comment, orig_line)
            elif m_sec_start:
                parser.on_section_start(comment, orig_line)
            elif m_sec_stop:
                parser.on_section_end(comment, orig_line)
            else:
                parser.on_unknown(orig_line)


class ScnParser:

    def __init__(self):
        pass

    def on_key_value(self, key, value, comment, orig):
        pass

    def on_section_start(self, comment, orig):
        pass

    def on_section_end(self, comment, orig):
        pass

    def on_unknown(self, orig):
        pass


class InfoScnParser(ScnParser):

    def __init__(self):
        super().__init__()

        self.section = 0
        self.search_path = []
        self.mas_files = []
        self.has_skyboxi = None

    def on_key_value(self, key, value, comment, orig):
        if self.section == 0:
            if key.lower() == "masfile":
                value = scn2posix_path(value)
                if posixpath.isabs(value):
                    value = value[1:]
                self.mas_files.append(value)
            elif key.lower() == "searchpath":
                self.search_path.append(scn2posix_path(value))
            elif key.lower() == "instance" and value.lower() == "skyboxi":
                self.has_skyboxi = True
            else:
                pass

    def on_section_start(self, comment, orig):
        self.section += 1

    def on_section_end(self, comment, orig):
        self.section -= 1


class SearchReplaceScnParser(ScnParser):

    def __init__(self, fout):
        super().__init__()

        self.fout = fout

        self.section = 0
        self.search_path = None
        self.mas_files = None

        self.delete_search_path = False
        self.delete_mas_file = False

        self.delete_next_section = False

    def on_key_value(self, key, value, comment, orig):
        if self.section == 0:
            if key.lower() == "instance" and value.lower() == "skyboxi":
                self.delete_next_section = True

            elif key.lower() == "masfile":
                if self.mas_files is not None:
                    for p in self.mas_files:
                        self.fout.write("MASFile=%s\n" % posix2scn_path(p))

                    self.mas_files = None
                    self.delete_mas_file = True

                elif not self.delete_mas_file:
                    self.fout.write(orig + '\n')

            elif key.lower() == "searchpath":
                if self.search_path is not None:
                    for p in self.search_path:
                        self.fout.write("SearchPath=%s\n" % posix2scn_path(p))

                    self.search_path = None
                    self.delete_search_path = True

                elif not self.delete_search_path:
                    self.fout.write(orig + '\n')

            else:
                self.fout.write(orig + '\n')
        else:
            if self.delete_next_section and self.section > 0:
                pass
            else:
                self.fout.write(orig + '\n')

    def on_section_start(self, comment, orig):
        self.section += 1
        if not self.delete_next_section:
            self.fout.write(orig + '\n')

    def on_section_end(self, comment, orig):
        self.section -= 1
        if not self.delete_next_section:
            self.fout.write(orig + '\n')
        else:
            if self.delete_next_section and self.section == 0:
                self.delete_next_section = False

    def on_unknown(self, orig):
        self.fout.write(orig + '\n')


# EOF #
