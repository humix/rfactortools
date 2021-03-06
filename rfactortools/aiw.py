# rFactor .aiw file processing tool
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


import PIL.Image
import PIL.ImageDraw
import math
import re

import rfactortools


keyvalue_regex = re.compile(r'^\s*([^=]+)\s*=\s*(.*)\s*')
vec3_regex = re.compile(r'\((-?\d*(\.\d*)?),\s*(-?\d*(\.\d*)?),\s*(-?\d*(\.\d*)?)\)')
int1_regex = re.compile(r'\((-?\d+)\)')


def vec3(str):
    m = vec3_regex.match(str)
    if m:
        x = float(m.group(1))
        y = float(m.group(3))
        z = float(m.group(5))
        return (x, y, z)
    else:
        raise Exception("not a vec3: \"%s\"" % str)


def int1(str):
    m = int1_regex.match(str)
    if m:
        return int(m.group(1))
    else:
        raise Exception("not a int1: \"%s\"" % str)


class AIW:

    def __init__(self):
        self.waypoints = []

    def get_waypoints(self, branch_id=0):
        return [w for w in self.waypoints if w.branch_id == branch_id]

    def get_bounding_box(self):
        x, y, z = self.waypoints[0].pos
        x1 = x
        y1 = z
        x2 = x
        y2 = z
        for w in self.waypoints[1:]:
            x, y, z = w.pos
            x1 = min(x1, x)
            y1 = min(y1, z)
            x2 = max(x2, x)
            y2 = max(y2, z)

        return x1, y1, x2, y2


class Waypoint:
    # wp_pos=(1615.28,115.8291,1235.497)
    # wp_perp=(-0.7424909,0,0.669856)
    # wp_normal=(0.003270742,0.999988,0.003625401)
    # wp_vect=(-2.192505,0.01757813,-2.429077)
    # wp_width=(12.5964,13.3416,25.1928,26.6832)
    # wp_dwidth=(25.1928,26.6832,0,0)
    # wp_path=(0,0.0)
    # wp_lockedAlpha=(0)
    # wp_galpha=(0)
    # wp_groove_lat=(0.000000)
    # wp_test_speed=(-1.0)
    # wp_score=(2,17900.64)
    # wp_cheat=(-1.0)
    # wp_pathabstractionspeed=(0.0000)
    # wp_pathabstraction=(0,-1)
    # wp_wpse=(0,0)
    # wp_branchID=(0)
    # wp_bitfields=(0)
    # wp_lockedLats=(1)
    # wp_multipathlat=(0.0, 0.0)
    # wp_translat=(0.0000, 0.0000)
    # wp_pitlane=(1)
    # WP_PTRS=(3632,1,-1,0)

    def __init__(self):
        self.pos = None
        self.bitfields = None
        self.branch_id = None


def parse_aiwfile(filename):
    aiw = AIW()

    with rfactortools.open_read(filename) as fout:
        parse_waypoints = False

        waypoint = Waypoint()
        for line in fout.read().splitlines():
            if line == "[Waypoint]":
                parse_waypoints = True

            if parse_waypoints:
                m = keyvalue_regex.match(line)
                if m:
                    key, value = m.group(1), m.group(2)
                    if key == "wp_pos":
                        waypoint = Waypoint()
                        aiw.waypoints.append(waypoint)
                        waypoint.pos = vec3(value)
                    elif key == "wp_bitfields":
                        waypoint.bitfields = int1(value)
                    elif key == "wp_branchID":
                        waypoint.branch_id = int1(value)
                    else:
                        pass  # logging.info("unhandled: \"%s\"" % key)

    return aiw


def point_distance(p1, p2):
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def draw_path(draw, scale, waypoints, ofx, ofy):
    # fudge factor to find hillclimb tracks that don't close
    d = point_distance(waypoints[0].pos, waypoints[-1].pos)
    if d < 200:
        waypoints.append(waypoints[0])

    x, y, z = waypoints[0].pos
    points = []
    for w in waypoints:
        x, y, z = w.pos
        points.append((x * scale + ofx, z * scale + ofy))

    draw.line(points, width=12*2, fill="#000000")
    draw.line(points, width=4*2, fill="#ffffff")


def render_aiw(aiw, width=512, height=512):
    x1, y1, x2, y2 = aiw.get_bounding_box()

    w = (x2 - x1)
    h = (y2 - y1)

    sx = width / w
    sy = height / h

    # make the image a little smaller then requested so the edges
    # aren't clipped
    scale = min(sx, sy) * 0.9

    # render at 2x scale to get a bit of anti-aliasing, rendering
    # quality is still much worse then cairo
    img = PIL.Image.new("RGBA", (width*2, height*2))

    ofx = width / 2 + (-x1 - w / 2) * scale
    ofy = height / 2 + (-y1 - h / 2) * scale

    draw = PIL.ImageDraw.Draw(img)
    draw_path(draw, scale*2.0, aiw.get_waypoints(0), ofx*2.0, ofy*2.0)

    img = img.resize((width, height), PIL.Image.ANTIALIAS)

    return img


# EOF #
