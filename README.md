# TermDash Package Manager

## TermDash Package
A **TermDash package** is a Python package designed to extend TermDash by providing one or more Textual UI components.

A TermDash package must:
- be installable using `pip`
- register itself using a Python entry point under the group `termdash.plugins`
- provide a `TermDashPlugin` object that describes how to load the plugin

A TermDash package may provide:
- a widget module (dashboard component)
- a page module (full screen view)
- configuration defaults
- custom CSS/theme assets


## Package Manager
The TermDash Package Manager is a CLI tool that manages TermDash packages.

The package manager is **not a replacement for pip**, but instead acts as a wrapper around pip to provide:
- discovery of available TermDash packages from a repository index
- installation/removal/update of TermDash packages
- tracking metadata about installed packages
- enabling/disabling packages through the TermDash config file

Internally, package installation is performed using:

```bash
python -m pip install <package source>
```
Where <package source> may be:
 - a git url
 - a local folder
 - a wheel file
 - a tarball file


## FAQ
Q: Why does this exist?
A: I wanted to make a package based terminal dashboard that could download packages to extend the functionality of the dashboard. To do this I needed some way to discover and download packages.


Q: What is a TermDash package?
A: A TermDash package is a pip-installable Python package that provides a Textual widget/page/service and registers itself using Python entrypoints so TermDash can discover and load it.


Q: How are packages stored?
A: TermDash packages are installed into the same Python environment as TermDash (typically a virtual environment). TermDash also maintains a local package database which stores package metadata such as:
- package id
- version
- install source URL
- install date
- update date
- repository origin
This database does not store package code, it only tracks installed packages and their sources.


Q: How are term packages downloaded?
A: TermDash packages are downloaded and installed using pip. The package manager resolves the package source URL (usually from a repository index file) and then installs it using:
```bash
python -m pip install git+<repo-url>
```


Q: Where are packages downloaded?
A:Packages are installed into the Python environment running TermDash. TermDash package manager metadata is stored in the user's data directory.



Q: How can I add my own packages to the package repository?
A:


Q: How are dependency conflicts resolved?
A: Dependency conflicts are resolved using pip’s dependency resolver. All TermDash packages share the same Python environment, so incompatible dependency requirements may prevent packages from installing together. TermDash does not currently sandbox packages or isolate dependencies.
Future improvements may include:
- per-package virtual environments
- isolated plugin execution (not planned for Phase 1)


Q: Are TermDash packages safe?
A: Inherently NO, I will do my best to make the default packages safe but downloading and using someone else TermDash packages is not safe. TermDash packages are just python code and this manager does nothing to make sure the code is not malicious. *IT IS UP TO THE USER TO VET ANY THIRD PARTY PACKAGES*


Q: If a package is enabled in the config but does not exist in the repo what happens?
A: If a package is enabled in the config but is not installed or discoverable, TermDash will skip loading it and output an error message. The package will not be automatically removed or modified unless the user runs a package manager command.



