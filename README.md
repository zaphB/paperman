# Latex Project and Bibliography Management Utilities

Paperman is a command line utility designed to accelerate your latex writing workflow by automating tasks as:
 * finding and copying frequently used images, bibtex entries and input tex-files from your other documents
 * identifying unused image files and bibtex entries in your latex project
 * maintaining consistent capitalization of, e.g., names in titles in bibtex entries
 * maintaining consistent usage of ISO4 abbreviated or full journal names
 * renaming and organizing downloaded bib and pdf files


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


# Usage

All functionality is available through the `paperman` shell command, which has a number of subcommands. Use `paperman --help` or `paperman <subcommand> --help` for a quick help.


## Managing a human-readable, searchable library for .pdf and .bib files

Paperman is capable of collecting and sorting pdf and bibliography data of literature to build up a human-readable library.


### `paperman collect`

This subcommand scans the folders given by the `library_collect_paths` in the config for pairs of pdf and bibliography files. If exactly one pdf and exactly one bibtex, or .ris bibliography file is found in one of the folders, the pair of files is moved to the library at `library_path`. Paperman creates subfolders in `library_path` which are named after the `library_folder_pattern`, which must be a valid format string to use with pythond `time.strftime(...)`. The time used to generate the folder name is the current time during the import, such you can later easily see from the folder structure which papers you added in which period of time.


### `paperman lib`

Without any options, `paperman lib` reports the status of your library, given by the number of valid papers and by lists of unpaired papers, duplicates and broken bib and pdf files. The command `paperman lib -f <query>` searches the library for entries that contain all given words in their bib file. With uppercase `-F <query>`, paperman does a fulltext search of the pdfs in the library and returns those that contain all given words. By default, the paths of matching entries are printed. The `-k` option allows to print the cite keys instead. The `-l` option prints the fill bibfile block.


### `paperman journal`

Paperman maintains a list of journal full names and their abbreviations. This list is populated with journals from [this database](https://www.cas.org/support/documentation/references/corejournals) and is automatically extended if previously unknown journals appear in newly added papers. The command `paperman journal` lists all known journals. The command `paperman journal <query>` lists all journals that match the query. By default both abbreviation and full journal name are displayed. The `-f` and `-a` options changed this behavior to only display abbreviated or full names.


## Managing images, bibliography and input files of a latex project

Paperman interprets any tex file in subfolders of the current directory that contains the `\begin{document}...\end{document}` environment as a toplevel file. Alternatively, the path to the desired latex toplevel file can be passed as an argument. The subcommands `img`, `bib` and `input` are used with the current directory being the base directory of a latex project and are able to detect unused and non-existing images, citations and inputs. Further, missing elements can be automatically imported if search paths are configured.

### `paperman img`

This subcommand lists missing and unused images of the current latex project. Only images directly included with the `\includegraphics{}` command are detected by paperman. The command `paperman img -i` automatically imports missing images, if it finds files with matching filenames on the paths given by `img_search_paths` in the config file. If multiple images are found, the setting `img_search_priority` can be a string containing 'newest', 'oldest' and 'path-order', to define how files are prioritized. Paperman prefers to store all images of a latex project in one subfolder of the project. This folder name can be configured with `img_dir_name`.


### `paperman bib`

This subcommand lists missing and unused citations of the current latex project. Only citations done with commands that contain cite in them, e.g. `\cite{...}`, `\fullcite{...}` or `\citeauthor{...}`, are detected by paperman. `paperman bib -i` automatically adds missing citations to the .bib file of the project if they can be found on the search paths configured by  `bib_search_paths` in the config. The field `bib_search_priority` allows defining which entry to prioritize in case of multiple found citations analogous to the `img` subcommand.

The `bib_repair` section contains a number of automatic fixes for bibtex files, as automatic journal name abbreviation/full name conversion, autogenerating a 'url' field if a 'doi' field is given, converting the pages field to contain only the beginning of the range, checking the capitalization of titles, and many more. Each repair rule can be switched on and off. The command `paperman bib -r` completely rewrites the current project's bibtex files and applies the repair rules to all entries.

If paperman is unsure if the forced capitalization of a title via additional `{...}` is appropriate or if paperman cannot find a journal in its database, it will ask for help interactively and store the answers in the config file for the next time.


### `paperman input`

This subcommand lists missing files in the current latex project which are required with the `\input{...}` command. Missing files can be automatically imported with `paperman input -i`. The search path for missing files is given by `input_search_paths` in the config, the search priority is given by `input_search_priority`.


### `paperman import-all`

This subcommand is a shortcut for `paperman img -i; paperman bib -i; paperman input -i` and imports all missing imgs, citations and input files to the current latex project.


## Building diff-pdfs

Paperman supports building diff-pdfs, in which additions and deletions between diferrent files or versions of the same file are highlighted. For this the programm `latexdiff` has to be installed on the `$PATH`.

### `paperman diff`

This subcommand expects two arguments that specify the names of the old and the new tex files. If bbl files with the matching file names exist for both old and new, paperman also builds a diff of the bibliography.

If the latex project is organized as a git repository, paperman is able to build diffs of different versions of one document. With the `-t` option, the first parameter is treated as a git tag name. With the `-T` option, the second parameter is treated as a tag name. Three different combinations are possible:
* Diff between a tagged version of a file and the current version of the file on disk, where the tagged version is treated as the "old" version: `paperman -t <tagname> <filename>`
* Diff between the current version of the file on disk and a tagged version of a file, where the version on disk is treated as the "old" version: `paperman -T <filename> <tagname>`
* Diff between two different tagged versions of a file: `paperman -tT <old-tagname> <new-tagname> <filename>`

To use tagged versions make sure to include the bbl files in your commits. Otherwise changes in the bibliography will not be visible.


## Checking latex projects for errors

Paperman is capable of scanning the tex files in your projects and reports suspicious-looking constructs that may not cause compilation errors but are prone to cause unintended behavior. E.g., it is good practice to avoid certain macros in the document and only use them in command definitions. The lists `lint.avoid_commands` and `lint.avoid_commands_in_toplevel` in the config file allow to define such commands for generaly tex files, or only for the toplevel files. If the `paperman lint` finds the listed commands it will print a message with path and line number.

### `paperman lint`

Like the other project related subcommands, `paperman lint` without arguments scans the entire project at the current location. Optionally, the path to a topleven file can be specified as an arguemnt.
 
