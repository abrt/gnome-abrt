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

Build dependencies can be listed by:

    $ ./autogen.sh sysdeps

or installed by:

    $ ./autogen.sh sysdeps --install

The dependency installer gets the data from [the rpm spec file](gnome-abrt.spec.in)

### Building from sources

When you have all dependencies installed run the following commands:

    $ ./autogen.sh --prefix=/usr --sysconfdir=/etc --localstatedir=/var --sharedstatedir=/var/lib
    $ make

### Checking

gnome-abrt uses pylint to validate source codes. If pylint prints out any issue,
the test will fail. Run the test by:

    $ make check

Configure pylint in [pylintrc](pylintrc).

Disable a particular pylint message in the source code by adding comment in the
following form:

    #pylint: disable=<message code>

### Running

If you want to run gnome-abrt from the source directory, you must configure
PYTHONPATH to point to `src/`. Makefile provides a convenient target for
running the tool from the source directory:

    $ make run

You can pass command line arguments trough `ARGS` environment variable:

    $ make run ARGS=-vvv

### Installing

If you need an rpm package, run:

    $ make rpm

otherwise check [INSTALL](INSTALL) for more details.
