# WORK IN PROGRESS

This repository will (eventually) replace googlefonts/noto-fonts as
the main distribution source for Noto fonts. For now, please continue
to go to https://fonts.google.com/noto to obtain individual Noto
fonts, and to https://github.com/googlefonts/noto-fonts to download
the entire collection.

To report an issue in a Noto font, go [here](http://notofonts.github.io/reporter.html).

## Build, QA and onboarding automation

The Noto project consists of a large number of GitHub repositories, and relies heavily on automated GitHub Actions to build, test, proof and release fonts. Here is an overview of how the automation works.

Each script repository is based on the [noto-project-template](https://github.com/notofonts/noto-project-template) repo. This provides two workflows, one for building and proofing fonts, and one which handles release and onboarding to Google Fonts.

* XXX Compare with previous
...

Repositories are organised by *script* but releases are organised by *family*. To create a release, push a new tag of the form `<Family>-v<Version>` (e.g. `NotoSansBengali-v2.002`). The `release` action will:

* build the fonts from source
* ensure that the tag is of the correct form, and extract the family name (`NotoSansBengali`) in which to find the fonts, and the "real" family name (`Noto Sans Bengali`) to be used in the Google Fonts PR
* create a GitHub release
* create a release bundle (Zip file)
* upload the release bundle to the release
* make a PR to Google Fonts

The Google Fonts PR requires organisational secrets `SSH_KEY` and `USER_GITHUB_TOKEN` to be set, and the `category` key to be set correctly in each `config.yaml` file.
