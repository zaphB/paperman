# Latex Project and Bibliography Management Utilities

Paperman is a command line utility designed to accelerate your latex writing workflow by automating tasks as:
 * finding and copying frequently used images, bibtex entries and input tex-files from your other tex documents
 * identifying unused image files and bibtex entries in your latex project
 * maintaining consistent capitalization of titles in bibtex entries
 * maintaining consistent usage of ISO4 abbreviated or full journal names in .bib files
 * organizing and maintaining your personal library of .bib and .pdf files
 * syncing your library to a tablet/ereader and keeping track of your annotated files


# Installation and configuration

Paperman requires python `>=3.6` and pip installed. Install the latest paperman version with

```
pip install paperman
```

or upgrade the installed version with

```
pip install --upgrade paperman
```

Running `paperman --version` should print the proper version number.

The entire configuration of paperman is stored in one config file. The location of this file depends on the operating system an can be printed with the `paperman config` command. `paperman config -o` can be used to open the config file in the editor `vim`, if vim is installed.


## Optional dependencies

If the [pyiso4](https://github.com/pierre-24/pyiso4) package is installed, paperman will suggest automatic abbreviation if encountering a new journal for the first time.


# Usage

All functionality is available through the `paperman` shell command, which has a number of subcommands. Use `paperman --help` or `paperman <subcommand> --help` for instructions on how to use possible options and parameters.

The behavior of paperman is controlled by its config file, which is a yaml formatted plain text file found at `~/.config/paperman/paperman.conf` on linux systems. Feel free to adjust the config according to your needs. Deleting an entry restores the default value on the next run of paperman.


## Managing a human-readable, searchable library for .pdf and .bib files

Paperman is capable of collecting and sorting pdf and bibliography data of literature to build up a human-readable library.


### `paperman collect`

This subcommand scans the folders given by the `library_collect_paths` (defaults to '\~/Desktop' and '\~/Downloads') in the config for pairs of pdf and bibliography files. If exactly one pdf and exactly one bibtex, or .ris bibliography file is found in one of the folders, the pair of files is moved to the library at `library_path` (defaults to '\~/Documents/bibliography'). Paperman creates subfolders in `library_path` which are named after the `library_folder_pattern` (defaults to '%Y-%m'), which must be a valid format string to use with python's `time.strftime(...)`. The time used to generate the folder name is the current time during the import, such you can later easily see from the folder structure which papers you added in which period of time.


### `paperman lib`

Without any options, `paperman lib` reports the status of your library, given by the number of valid papers and by lists of unpaired papers, duplicates and broken bib and pdf files. The command `paperman lib -f <query>` searches the library for entries that contain all given words in their bib file. With uppercase `-F <query>`, paperman does a fulltext search of the pdfs in the library and returns those that contain all given words. By default, the paths of matching entries are printed. The `-k` option allows to print the cite keys instead. The `-l` option prints the fill bibfile block.


### `paperman journal`

Paperman maintains a list of journal full names and their abbreviations. This list is initially populated with journals from [this database](https://www.cas.org/support/documentation/references/corejournals) and is automatically extended if previously unknown journals appear in newly added papers. The command `paperman journal` lists all known journals. The command `paperman journal <query>` lists all journals that match the query. By default both abbreviation and full journal name are displayed. The `-f` and `-a` options change this behavior to only display abbreviated or full names.


### `paperman sync`

Without any options, `paperman sync` tries to sync your library's pdf files with the device mounted at the path given by the `library_sync_device` config entry. To manually pass a mount point, use the `-p` option. Documents older than the value of the config entry `library_sync_max_age` in seconds are ignored when syncing, where the time that passed since the "last modified" time of the pdf is taken as its age. Any pdf found on the sync device that does not exist in the local library, or has a different size than its counterpart in the local library, is copied to the subfolder 'annotated' in the local library.


## Managing images, bibliography and input files of a latex project

Paperman interprets any tex file in subfolders of the current directory that contains the `\begin{document}...\end{document}` environment as a toplevel file. Alternatively, the path to the desired latex toplevel file can be passed as an argument. The subcommands `img`, `bib` and `input` are used with the current directory being the base directory of a latex project and are able to detect unused and non-existing images, citations and inputs. Further, missing elements can be automatically imported if search paths are configured.

### `paperman img`

This subcommand lists missing and unused images of the current latex project. Only images directly included with the `\includegraphics{}` command are detected by paperman. The command `paperman img -i` automatically imports missing images, if it finds files with matching filenames on the paths given by `img_search_paths` (defaults to '\~/Documents') in the config file. If multiple images are found, the setting `img_search_priority` (defaults to 'path-order, newest') can be a string containing 'newest', 'oldest' and 'path-order', to define how files are prioritized. Paperman prefers to store all images of a latex project in one subfolder of the project. This folder name can be configured with `img_dir_name` (defaults to 'img').

### `paperman bib`

This subcommand lists missing and unused citations of the current latex project. Only citations done with commands that contain cite in them, e.g. `\cite{...}`, `\fullcite{...}` or `\citeauthor{...}`, are detected by paperman. `paperman bib -i` automatically adds missing citations to the .bib file of the project if they can be found on the search paths configured by  `bib_search_paths` (defaults to '\~/Documents') in the config. The field `bib_search_priority` (defaults to 'path-order, newest') allows defining which entry to prioritize in case of multiple found citations, analogous to the `img` subcommand.

The `bib_repair` config section contains a number of automatic fixes for bibtex files, as automatic journal name abbreviation/full name conversion, autogenerating a 'url' field if a 'doi' field is given, converting the pages field to contain only the beginning of the range, checking the capitalization of titles, and many more. Each repair rule can be switched on and off. The command `paperman bib -r` completely rewrites the current project's bibtex files and applies the repair rules to all entries.

If paperman is unsure if the forced capitalization of a title via additional `{...}` is appropriate or if paperman cannot find a journal in its database, it will ask for help interactively and store the answers in the config file for the next time.

### `paperman input`

This subcommand lists missing files in the current latex project which are required with the `\input{...}` command. Missing files can be automatically imported with `paperman input -i`. The search path for missing files is given by `input_search_paths` (defaults to '\~/Documents') in the config, the search priority is given by `input_search_priority` (defaults to 'path-order, newest').

### `paperman import-all`

This subcommand is a shortcut for `paperman img -i; paperman bib -i; paperman input -i` and imports all missing imgs, citations and input files to the current latex project.


## Building diff-pdfs

Paperman supports building diff-pdfs, in which additions and deletions between diferrent files or versions of the same file are highlighted. For this the programm `latexdiff` has to be installed on the `$PATH`.

### `paperman diff`

This subcommand expects two arguments that specify the names of the old and the new tex files. If bbl files with matching file names exist for both old and new, paperman also builds a diff of the bibliography.

If the latex project is organized as a git repository, paperman is able to build diffs of different versions of one document. With the `-t` option, the first parameter is treated as a git tag name. With the `-T` option, the second parameter is treated as a tag name. Three different combinations are possible:
* Diff between a tagged version of a file and the current version of the file on disk, where the tagged version is treated as the "old" version: `paperman diff -t <tagname> <filename>`
* Diff between the current version of the file on disk and a tagged version of a file, where the version on disk is treated as the "old" version: `paperman diff -T <filename> <tagname>`
* Diff between two different tagged versions of a file: `paperman diff -tT <old-tagname> <new-tagname> <filename>`

To use tagged versions make sure to include the bbl files in your commits. Otherwise changes in the bibliography will not be visible.


## Checking latex projects for errors

Paperman is capable of scanning the tex files in your projects and reports suspicious-looking constructs that may not cause compilation errors but are prone to cause unintended behavior. E.g., it is good practice to avoid certain macros in the document and only use them in command definitions. The lists `lint.avoid_commands` and `lint.avoid_commands_in_toplevel` in the config file allow to define such commands for general tex files, or for the toplevel files only. If `paperman lint` then finds the listed commands in tex files of the project will print a warning message including path and line number of the found command. Adding a '%nolint' comment to a line in a latex file disables any linter warnings generated by that line.

### `paperman lint`

Like the other project related subcommands, `paperman lint` without arguments scans the entire project at the current location. Optionally, the path to a toplevel file can be specified as an argument.


## Cleaning latex build files

The countless build files generated by latex pollute latex project directories, make it difficult to find relevant files, and waste space in backups.

### `paperman clean`

This subcommand crawls recursively through the subfolders of the current directory and moves all files that look like latex build files to a trash folder `clean.trash_folder` (defaults to '\~/Desktop/paperman-trash'). `clean.ignore_paths` specifies a list of paths that `paperman clean` will never recurse into. Any directory that contains files with all suffixes listed in `clean.required_suffs` is considered a latex directory and all files ending with suffixes `clean.clean_suffs` will be removed. This subcommand skips any directory that starts with a dot.
