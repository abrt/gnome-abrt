i18n.merge_file(
  input: 'org.freedesktop.GnomeAbrt.metainfo.xml.in',
  install: true,
  install_dir: join_paths(datadir, 'metainfo'),
  output: 'org.freedesktop.GnomeAbrt.metainfo.xml',
  po_dir: join_paths(meson.project_source_root(), 'po'),
  type: 'xml'
)

i18n.merge_file(
  input: 'org.freedesktop.GnomeAbrt.desktop.in',
  install: true,
  install_dir: join_paths(datadir, 'applications'),
  output: 'org.freedesktop.GnomeAbrt.desktop',
  po_dir: join_paths(meson.project_source_root(), 'po'),
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

if pylint.found()
  lint_env = environment({
    'GDK_BACKEND': '-',
  })
  test('lint', pylint,
    args: [
      # This will not fail during configuration if pylintrc is missing:
      # https://github.com/mesonbuild/meson/issues/6175
      '--rcfile=@0@'.format(join_paths(meson.project_source_root(), 'pylintrc')),
      '--limit-inference-results=5',
      'gnome-abrt',
      'gnome_abrt',
    ],
    depends: [
      gnome_abrt_wrappers_module,
    ],
    env: lint_env,
    timeout: 180, # 3 minutes
    workdir: meson.current_build_dir(),
  )
endif
