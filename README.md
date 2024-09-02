
To report an issue in a Noto font, go [here](http://notofonts.github.io/reporter.html).

## High level overview and instructions for font developers

Here's what you need to know for general font-level work on the Noto project:

* Each *script* in Noto gets its own repository. The script repository is based on the [noto-project-template](https://github.com/notofonts/noto-project-template) repo. If you are in the position of needing to **add a new script to Noto**, do so by visiting https://github.com/notofonts/noto-project-template and clicking the green "Use this template" button. *Make sure you click the "Include all branches" option on the page which follows.*

* Each *family* within a script gets its own configuration file, `sources/config-<something>.yaml`. In many cases, you will want to automatically add a subset of glyphs from Noto Sans, Noto Serif or Noto Devanagari into the source UFOs. You can do this by adding the following to the configuration file:

```yaml
includeSubsets:
  - name: "GF Glyph Sets/GF-latin-core"
    from: "Noto Sans"
```

or

```yaml
includeSubsets:
  - from: "Noto Sans Devanagari"
    ranges:
        - from: 0x1CD0
          to: 0x1CE7
        - from: ...
```

These subsets will be added to the font by Notobuilder, explained below.

* Try to work on font problems in branches and make pull requests. When you work in a branch, GitHub actions will build the font, perform QA tests, and create QA reports and proof sheets. You can download these reports as a build artefact by going to the "Actions" page.

* As well as the GitHub actions, you can trigger builds and tests manually using the Makefile:
    - `make build` builds the font
    - `make test` runs the fontbakery checks

* The following QA tests are run: 
    * Fontbakery is run using the `notofonts` profile for the non-"full" builds and using the `googlefonts` profile for any outputs that are destined for Google Fonts onboarding. Fontbakery is also configured so that any [shaping tests](https://simoncozens.github.io/tdd-for-otl/) found in `qa/shaping_tests` are automatically run.
    * The previous released version of the font is fetched and `gftools.diffenator` is run to produce a report showing the differences. As well as the glyph-level differences, any strings found in files matching `qa/*.txt` are rendered and their differences are displayed.
    * Proof sheets are generated with `gftools-gen-html proof`.

* In addition, the artefacts (latest font builds and QA reports) from the current `main` branch are published on the repository's GitHub Pages site. (see e.g. https://notofonts.github.io/vithkuqi/)

* Repositories are organised by *script* but releases are organised by *family*. **When it's time to create a new release**, push a new tag of the form `<Family>-v<Version>` (e.g. `NotoSansBengali-v2.002`). If everything goes well, the release GitHub Action will then:
    * Build and test the font.
    * Create a GitHub Release including a Zip file of font binaries.
    * Create a PR to Google Fonts to onboard the new release.

> Note that the action to produce the Google Fonts PR requires the organisational secrets `SSH_KEY` and `USER_GITHUB_TOKEN` to be set, and the `category` key to be set correctly in each `config.yaml` file.

## Build, QA and onboarding automation

All of the above is wonderful if everything works. Here's what you need to know if there are problems with the build process itself.

The main design goal for the build process has been *forward compatibility*. In other words, providing a consistent build experience across all Noto script project repositories while ensuring that any changes which need to be made to the build or its environment do not need to be repeated across all 150+ repos.

The main way this is achieved is through the [notobuilder](https://github.com/notofonts/notobuilder) repository. All script repositories use notobuilder, which provides:

* The GitHub workflows which control building (`build.yaml`) and releasing (`release.yaml`).
* A declaration (through its `setup.py`) of the Python dependencies and their versions used to build all Noto fonts.
* The build process itself. (We will discuss below why Noto needs its own bulid process!)
* The QA process.

The aim is that Noto project repositories would pull the latest version of this
repository and use to get the latest actions as well as to use it to build the fonts; this means that both the way that font building happens, and the required versions of fonttools, fontmake, etc., can all be defined and updated in one single place, and also that any updates to the build methodology or the required versions will be automatically carried over to new builds.

### notobuilder

The `Notobuilder` class is a subclass of [GFBuilder](https://github.com/googlefonts/gftools),
but with certain modifications to suit the Noto workflow. 

* We expect a certain directory structure for the output files:
    - `fonts/<family>/unhinted/variable-ttf`
    - `fonts/<family>/unhinted/otf`
    - `fonts/<family>/unhinted/ttf`
    - `fonts/<family>/hinted/ttf`
* In Noto, we produce unhinted and hinted versions of the font; hinted versions
are produced by trying to run ttfautohint with an appropriate script (`-D`) flag. (If autohinting fails, the unhinted font is copied to the hinted font path without erroring out.)
* We try to produce a variable font by default but also don't error out if that fails.
* We also (based on a configuration file) use UFO merging to add subsets of Noto Sans, Noto Serif or Noto Sans Devanagari into the sources to produce a "full" build of the font.

As these are Noto-specific process requirements they have not been merged into the upstream GFBuilder.

### notoqa

This Python module defines the process used to test Noto fonts. In a similar vein to [notobuilder](https://github.com/notofonts/notobuilder/), the point is that we define the test procedures in one location, and all project repositories automatically receive updated versions of the test protocols when this repository changes.

It defines two kind of tests:

* `python -m notoqa` runs fontbakery checks on each family, and is used to implement the `make test` target in the project repository Makefile.

* `python -m notoqa.regression` downloads the latest release of the family and runs regression tests between the current build and the previous, using `gftools.qa`.

## Note
This repository does not contain the following fonts:

* Noto CJK fonts: https://github.com/notofonts/noto-cjk
* Noto Emoji: https://github.com/googlefonts/noto-emoji

## Licensing

All Noto fonts (in the `fonts/` directory) are licensed under the [SIL Open Font License](fonts/LICENSE). This documentation and all tooling in this repository is licensed under the [Apache 2.0 License](LICENSE).
