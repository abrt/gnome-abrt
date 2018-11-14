resource_files =                      \
	$(shell $(GLIB_COMPILE_RESOURCES) \
		--sourcedir=$(srcdir)         \
		--sourcedir=$(builddir)       \
		--generate-dependencies       \
		$(srcdir)/org.freedesktop.GnomeAbrt.gresource.xml) 

org.freedesktop.GnomeAbrt.gresource: org.freedesktop.GnomeAbrt.gresource.xml $(resource_files)
	$(AM_V_GEN) \
		$(GLIB_COMPILE_RESOURCES)   \
			--target=$@             \
			--sourcedir=$(srcdir)   \
			--sourcedir=$(builddir) \
			$<

resourcedir = $(pkgdatadir)
resource_DATA = org.freedesktop.GnomeAbrt.gresource

CLEANFILES = \
	org.freedesktop.GnomeAbrt.gresource

EXTRA_DIST =      \
	$(resource_files) \
	org.freedesktop.GnomeAbrt.gresource.xml
