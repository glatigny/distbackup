# Distbackup Configuration file

The configuration file for Distbackup is a using the INI format.
The backup process will execute each group one by one.

A configuration group have that format:
```ini
[group name]
type=action to perform
param1=...
param2=...
```

## Default group

There is one special group named **default**.
That group contains the default values for some settings, like the exclusion list or the output folder.
```ini
[default]
exclude=.svn, .git
output=/home/backup/latest/
archive=/home/backup/test/
```

## Backup action types

When you add a group in the configuration, there is a mandatory setting which will define the type.
Depending the chosen type, the rest of the parameter can change.

### report

The report action allow you to output some text. It can be a fixed text but it can also be something more dynamic.

When you use the ``report`` type, you have to specify the parameter ``report`` to indicate what content you will provide.
Please note that if you provide some text, you can use tags (variables).

So you can display a backup introduction:
```ini
[report:intro]
type=report
report=text
value=Backup started on {now}
	_
```

Or displaying some statistics:
```ini
[report:stats]
type=report
report=text:tree,disk
tree={tree:archive}
disks=/,/home
```

The parameter ``report`` can have several values separated by coma.

The ``text`` value allow you to provide some fixed text content. That content will be placed in the ``value`` parameter.
But you can indicate in which parameter you want to put your content, like in the second sample with ``text:tree``.

The ``disk`` value allow you to display disk usage statistics.
If you have several disk, you can specify the mounting point to want to display in the ``disks`` parameter.

*If you have idea or request about new report features, feel free to create a feature request*

#### Report - tags (variables)

**{now}** will display the current date using the format *Y-m-d H:M*

**{year}**, **{month}**, **{day}**, **{hour}**, **{minute}**, **{second}** will display the specific date information.

**{size:output}**, **{size:archive}** will display the total size of the output folder or of the archive folder.

**{tree:archive}** will display the number of files (and the size of these files) for each folder in the ``archive``.

### dpkg

That action is specific to OS using [dpkg](https://en.wikipedia.org/wiki/Dpkg) package management system (*debian*, *ubuntu*, ...).

It will create a file with the selected (installed) packages in your environnement.
You need to specify the ``output`` file in the ``output`` parameter.

```ini
[dpkg]
type=dpkg
output=/etc/dpkg-selection
```

### folder

The ``folder`` action will create a compressed archive with the content of the targeted folder.
By default the archive will be a **tar.gz** file.

```ini
[folder:etc]
type=folder
name=etc
group=system
folder=/etc/
output=etc
```

The parameter ``folder`` indicates the directory that you want to backup and store into an archive.

The parameter ``output`` contains the name of the generated file.
That file will be stored in the output folder you have specified in the **default** group.

The parameter ``group`` is optional but is useful for the **archive** and **clean** processes.
By specifying a group you can regroup files together and have different restrictions (like the storage duration).

The parameter ``name`` is optional but can be use to improve the output display.
If you do not specify a name, the value of the ``folder`` will be display in the output.

By default, the ``exclude`` list will be used while performing the backup of the folder.
But you can specify an ``exclude`` parameter per group in order to override the **default** settings.

### svn

The ``svn`` action is useful when you are hosting subversion repositories.
It will perform a *svn dump* 

```ini
[svn:test]
type=svn
name=TestSvn
group=local
folder=/home/local/svn/test/
output=local.svn.test
```

The parameters of ``svn`` are mostly the same than the ``folder`` ones.
Except that ``svn`` do not use exclusion.

### db

The ``db`` (or ``database``) action allow you to perform a local database backup.
Distbackup is currently compatible with *MySQL*, *PostgreSQL* and *MongoDB*.

```ini
[db:mysql]
type=db
name=MySQL
group=local
output=db.mysql
driver=mysql
database=all
user=root
password=**********
```

The ``driver`` parameter specify the type of your database (**mysql**, **pgsql**, **mongodb**).

The ``database`` parameter allow you to target specific base (or collection).
You can use the value **all** in order to perform a full backup.

The ``user`` and ``password`` parameters are used for the connection credentials.
Please note that the password is in clear text so it is recommanded to use an account with limited accesses and to secure your distbackup configuration file.

### sync

The ``sync`` action allow you to copy backup files in another place.
It handle several protocols: **archive**, **copy**, **rsync**, ***ftp***

When using the **rsync** protocol, you need to specify an ``host`` for the destination.
It will copy all files you have backup during that session (in the ``output`` folder).
```ini
[sync:external]
type=sync
protocol=rsync
host=rsyncaccount@rsynchost:/home/backup/test/
```

The **archive** protocol is special because it will archive the backup files into another folder (specify in the ``default`` group).
Each file will be stored in a folder depending the ``group`` value you gave him.
```ini
[sync:archive]
type=sync
protocol=archive
```
During the archive, each file will be renamed and will receive a sufix with the current date.

### clean

The ``output`` folder will only contain the latest backup files but the ``archive`` folder.

The ``clean`` action allow you to delete old backups in the ``archive`` folder.
You can specify the number of ``days`` you want to keep. Older files will be removed.
```ini
[clean:archive]
type=clean
days=5
```
