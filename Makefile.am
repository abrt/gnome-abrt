ACLOCAL_AMFLAGS = -I m4
SUBDIRS = src po doc icons

EXTRA_DIST = gnome-abrt.spec.in asciidoc.conf gnome-abrt-version gnome-abrt-release

RPM_DIRS = --define "_sourcedir `pwd`" \
	   --define "_rpmdir `pwd`" \
	   --define "_specdir `pwd`" \
	   --define "_builddir `pwd`" \
	   --define "_srcrpmdir `pwd`"

rpm:
	./gen-version | head -1 | tr -d "\n" > gnome-abrt-version
	./gen-version | tail -1 | tr -d "\n" > gnome-abrt-release
	autoconf --force
	$(MAKE) dist
	rpmbuild $(RPM_DIRS) -ba gnome-abrt.spec

srpm:
	./gen-version | head -1 | tr -d "\n" > gnome-abrt-version
	./gen-version | tail -1 | tr -d "\n" > gnome-abrt-release
	autoconf --force
	$(MAKE) dist
	rpmbuild $(RPM_DIRS) -bs gnome-abrt.spec

run: all dist
	cp src/gnome_abrt/wrappers/.libs/_wrappers.so src/gnome_abrt/wrappers/
	PYTHONPATH="../src" ./src/gnome-abrt

UPLOAD_LOGIN ?= $(USER)
UPLOAD_URL ?= fedorahosted.org

upload: dist
	scp gnome-abrt-$(VERSION).tar.gz $(UPLOAD_LOGIN)@$(UPLOAD_URL):abrt
