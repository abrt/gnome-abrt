## Copyright (C) 2012 ABRT team <abrt-devel-list@redhat.com>
## Copyright (C) 2001-2005 Red Hat, Inc.

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA  02110-1335  USA

from config import get_configuration
from views import OopsWindow
from problems import (ProblemSource, Problem, MultipleSources)
from dbus_problems import DBusProblemSource
from directory_problems import DirectoryProblemSource
from controller import Controller
from errors import (UnavailableSource, InvalidProblem)
import l10n

def init():
    l10n.init('gnome-abrt')
