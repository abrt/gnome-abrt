# coding=UTF-8

## Copyright (C) 2013 ABRT team <crash-catcher@lists.fedorahosted.org>
## Copyright (C) 2013 Red Hat, Inc.

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

from gnome_abrt.url import gliburltitle

__ASYNC_WORKER = gliburltitle.get_url_title_async

def set_async_worker(worker):
    global __ASYNC_WORKER
    __ASYNC_WORKER = worker

def get_url_title_async(url, callback, user_data):
    __ASYNC_WORKER(url, callback, user_data)
