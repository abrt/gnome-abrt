ACLOCAL_AMFLAGS = -I m4
SUBDIRS = src po

EXTRA_DIST = gnome-abrt.spec.in

RPM_DIRS = --define "_sourcedir `pwd`" \
	   --define "_rpmdir `pwd`" \
	   --define "_specdir `pwd`" \
	   --define "_builddir `pwd`" \
	   --define "_srcrpmdir `pwd`"

rpm:
	autoconf --force
	$(MAKE) dist
	rpmbuild $(RPM_DIRS) -ba gnome-abrt.spec

srpm:
	autoconf --force
	$(MAKE) dist
	rpmbuild $(RPM_DIRS) -bs gnome-abrt.spec
