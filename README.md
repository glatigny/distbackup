# DistBackup

Python script to backup your Linux distribution

## Installation

* Copy the `distbackup.py` file in your `/usr/local/sbin` folder.
* Give it execution permission (0750)
* Create your main backup configuration `/etc/distbackup.cfg`

## Usage

`distbackup.py`
* `-c [config file]` use a specific configuration file.
* `--debug` process the configuration without executing the backup.

## License

* Copyright (C) 2015 Obsidev (Glatigny Jerome). All rights reserved.
* Distributed under the GNU General Public License version 2 or later