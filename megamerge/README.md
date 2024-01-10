# Noto Megamerged

*This directory is currently experimental and not an official Noto
release. If it breaks, you get to keep both pieces.*

This directory contains a Python script to generate single fonts
covering all of the living and historical scripts in Noto, subject to
the following caveats:

* Only the Regular weight is included.
* The fonts are merged with `fontTools.merger`, which *might* work well enough for your use case. Equally, it might not.
* Vertical metrics are removed.
