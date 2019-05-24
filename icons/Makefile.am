NULL =

icondir = $(datadir)/icons
nobase_icon_DATA = \
	hicolor/scalable/apps/org.freedesktop.GnomeAbrt.svg \
	hicolor/symbolic/apps/org.freedesktop.GnomeAbrt-symbolic.svg \
	$(NULL)

themes = \
	hicolor \
	$(NULL)

EXTRA_DIST = $(nobase_icon_DATA)

###############################################################################

gtk_update_icon_cache = gtk-update-icon-cache -f -t

update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating GTK icon cache"; \
		for theme in $(themes); do \
			$(gtk_update_icon_cache) $(datadir)/icons/$$theme; \
		done; \
	else \
		echo "*** Icon cache not updated.  After (un)installing, run this:"; \
		for theme in $(themes); do \
			echo "***   $(gtk_update_icon_cache) $(datadir)/icons/$$theme"; \
		done; \
	fi

install-data-hook: update-icon-cache
uninstall-hook: update-icon-cache
