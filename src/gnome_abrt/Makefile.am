SUBDIRS = wrappers url

gnome_abrtexecdir = $(pyexecdir)/gnome_abrt

gnome_abrtexec_PYTHON = \
	__init__.py \
	application.py \
	config.py \
	controller.py \
	dbus_problems.py \
	directory_problems.py \
	errors.py \
	problems.py \
	signals.py \
	tools.py \
	views.py \
	l10n.py \
	desktop.py

controller.py: controller.py.in Makefile
	sed -e s,\@libexecdir\@,$(libexecdir),g $< > $@

__init__.py: __init__.py.in Makefile
	sed -e s,\@PACKAGE\@,$(PACKAGE),g \
	-e s,\@VERSION\@,$(VERSION),g \
	-e s,\@PKGDATADIR\@,$(pkgdatadir),g \
	-e s,\@localedir\@,$(localedir),g $< > $@

EXTRA_DIST = __init__.py.in controller.py.in

DISTCLEANFILES = __init__.py controller.py

all-local: __init__.py controller.py

check-local: $(gnome_abrtexec_PYTHON)
if USE_PYLINT
	PYLINT=$(PYLINT) PYLINTRC=$(top_builddir)/pylintrc $(top_builddir)/runpylint.sh $(abs_builddir)
endif
