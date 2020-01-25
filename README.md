# gnome-abrt

**A utility for viewing problems that have occurred with the system.**

### About

gnome-abrt is a graphical user interface which allows users to analyze and
report application crashes, system failures and other problems.

The tool was developed according to [Oops!](https://live.gnome.org/Design/Apps/Oops)

gnome-abrt is part of [the ABRT project](https://github.com/abrt/).

### Development

 * IRC Channel: #abrt on FreeNode
 * [Mailing List](https://lists.fedorahosted.org/admin/lists/crash-catcher.lists.fedorahosted.org/)
 * [Bug Reports and RFEs](https://github.com/abrt/gnome-abrt/issues)
 * [Contributing to gnome-abrt](CONTRIBUTING.md)

### Development dependencies

Build dependencies can be installed using:

    # dnf builddep --spec gnome-abrt.spec

### Building from sources

When you have all dependencies installed run the following commands:

    $ meson build
    $ ninja -C build

### Checking

gnome-abrt uses pylint to validate source codes. If pylint prints out any issue,
the test will fail. Run the test by:

    $ ninja -C build test

Configure pylint in [pylintrc](pylintrc).

Disable a particular pylint message in the source code by adding comment in the
following form:

    #pylint: disable=<message code>

### Running

A run target is provided for running gnome-abrt with built changes:

    $ ninja -C build run

### Installing

If you need an rpm package, run:

    $ ninja -C build rpm
