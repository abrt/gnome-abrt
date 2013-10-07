## Copyright (C) 2013 ABRT team <abrt-devel-list@redhat.com>
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

import os
import signal
import logging
import fcntl

import gi
#pylint: disable=E0611
from gi.repository import GLib

#pylint: disable=W0613
def _handle_signal_sigchld(callback, data):
    child_exited = False
    while True:
        try:
            # We don't care about child's status (2. ret val)
            chpid, _ = os.waitpid(-1, os.WNOHANG)
            if chpid == 0:
                # Break otherwise we would cycle until all children are exited
                logging.debug("There are still children processes running")
                break
            child_exited = True
        except OSError as ex:
            # Breaks once no child is waiting
            logging.debug(ex)
            break

    # If no child exited then return immediately because no action is necessary
    if not child_exited:
        logging.debug("Got SIGCHLD but no child exited")
        return

    if data is not None:
        callback(data)
    else:
        callback()

def sigchld_signal_handler(callback, data=None):
    signal.signal(signal.SIGCHLD,
            lambda signum, frame: _handle_signal_sigchld(callback, data))


#pylint: disable=W0613
def _gsource_handle_signal(source, condition, data):
    # Read all bytes, SIGCHLD could be received more than once but we want to
    # call the callback only once. So, read all bytes from GIOChannel
    while source.read():
        pass

    if data[1] is not None:
        data[0](data[1])
    else:
        data[0]()

    # True -> keep this source attached to the context
    return True

def _giochannel_notice_sigchld_signal(wfd):
    os.write(wfd, '1')

def glib_sigchld_signal_handler(callback, data=None):
    pipes = os.pipe()
    fcntl.fcntl(pipes[0], fcntl.F_SETFD, fcntl.FD_CLOEXEC)
    fcntl.fcntl(pipes[1], fcntl.F_SETFD, fcntl.FD_CLOEXEC)

    sigchld_signal_handler(_giochannel_notice_sigchld_signal, pipes[1])

    channel = GLib.IOChannel(pipes[0])
    channel.set_flags(GLib.IOFlags.NONBLOCK)

    if gi.version_info < (3, 7, 2):
        channel.add_watch(GLib.IOCondition.IN,
                _gsource_handle_signal, (callback, data))
    else:
        GLib.io_add_watch(channel, GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN,
                _gsource_handle_signal, (callback, data))
