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
  pure: true,
  subdir: 'gnome_abrt/wrappers',
)
