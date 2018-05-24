# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from Products.Archetypes.Widget import InAndOutWidget


class PMInAndOutWidget(InAndOutWidget):
    """Override to use another rendering macro.
       The new rendering macro will just display elements under each other using
       <br> separator instead one next to the other using default ', ' separator."""

    _properties = InAndOutWidget._properties.copy()
    _properties.update(
        {'macro': "pminandout",
         'view_use_breakline_separator': True})
