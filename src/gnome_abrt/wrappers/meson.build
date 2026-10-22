gnome_abrt_wrappers_sources = [
  '__init__.py',
]

foreach file: gnome_abrt_wrappers_sources
  configure_file(
    copy: true,
    input: file,
    output: file,
  )
endforeach

python_installation.install_sources(gnome_abrt_wrappers_sources,
  pure: false,
  subdir: 'gnome_abrt/wrappers',
)

gnome_abrt_wrappers_module_sources = [
  'common.h',
  'module.c',
  'problem_app.c',
]

gnome_abrt_wrappers_module = python_installation.extension_module('_wrappers', gnome_abrt_wrappers_module_sources,
  subdir: 'gnome_abrt/wrappers',
  dependencies: [
    gio_dep,
    libreport_gtk_dep,
    pygobject_dep,
    python_dep
  ],
  install: true,
)
