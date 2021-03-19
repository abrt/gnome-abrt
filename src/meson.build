i18n.merge_file(
  input: 'org.freedesktop.GnomeAbrt.appdata.xml.in',
  install: true,
  install_dir: join_paths(datadir, 'metainfo'),
  output: 'org.freedesktop.GnomeAbrt.appdata.xml',
  po_dir: join_paths(meson.source_root(), 'po'),
  type: 'xml'
)

i18n.merge_file(
  input: 'org.freedesktop.GnomeAbrt.desktop.in',
  install: true,
  install_dir: join_paths(datadir, 'applications'),
  output: 'org.freedesktop.GnomeAbrt.desktop',
  po_dir: join_paths(meson.source_root(), 'po'),
  type: 'desktop'
)

gnome_abrt_main = configure_file(
  copy: true,
  input: 'gnome-abrt',
  install: true,
  install_dir: bindir,
  output: 'gnome-abrt',
)

subdir('gnome_abrt')

if runpylint.found()
  test('lint', runpylint,
    args: [
      # This will not fail during configuration if pylintrc is missing:
      # https://github.com/mesonbuild/meson/issues/6175
      '--rcfile=@0@'.format(join_paths(meson.source_root(), 'pylintrc')),
      'gnome-abrt',
      'gnome_abrt',
    ],
    workdir: meson.current_build_dir(),
    depends: [
      gnome_abrt_wrappers_module,
    ],
    timeout: 120, # 2 minutes
  )
endif
