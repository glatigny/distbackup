#! /usr/bin/python
#
# distbackup.py: script to backup your Linux distribution
#
# https://github.com/obsidev/distbackup
#
####################################################

import sys
import os
import stat
import re
import time
import shutil
import subprocess
import getopt
import datetime
import ConfigParser
import gzip

####################################################

#
#
#
class DatabaseBackup:
    """Backup a database.

    Because there is several database driver, a class is used.
    """

    @staticmethod
    def process(settings, section):
        """Process the backup with the right database handler
        """
        handler = settings.get(section, 'driver')

        if not handler in ['mysql','pgsql','mongodb']:
            return False

        archive_format = 'gz'
        output_folder = settings.get('default', 'output')
        output_filename = settings.get(section, 'output') + '.' + archive_format
        output_file = os.path.join(output_folder, output_filename)

        # Call the right handler
        syncMethod = getattr(DatabaseBackup, handler)
        return syncMethod(settings, section, output_file)

    @staticmethod
    def mysql(settings, section, output_file):
        """Mysql backup handler

        Should not be called directly
        """
        params = ['mysqldump']
        if not settings.has_option(section, 'database') or settings.get(section, 'database') == 'all':
            params.append('-A')
        else:
            params.append('--databases')
            params.append(settings.get(section, 'database'))

        if settings.has_option(section, 'user'):
            params.append('--user=' + settings.get(section, 'user'))
        if settings.has_option(section, 'password'):
            params.append('--password=' + settings.get(section, 'password'))

        # Debug mode
        if debug:
            print DBG_MSG + "* MySQL dump -> " + output_file + DBG_MSG_END
            return {'file': output_file}

        # Processing the dump
        mysqldump = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        dump_output = mysqldump.communicate()[0]

        f = gzip.open(output_file, 'wb')
        f.write(dump_output)
        f.close()

        return {
            'file': output_file
        }

    @staticmethod
    def pgsql(settings, section, output_file):
        """PostgreSQL backup handler

        Should not be called directly
        """
        params = ['mysqldump']
        if not settings.has_option(section, 'database') or settings.get(section, 'database') == 'all':
            params = ['pg_dumpall']
        else:
            params = ['pg_dump', settings.get(section, 'database')]

        # Debug mode
        if debug:
            print DBG_MSG + "* PostgreSQL dump -> " + output_file + DBG_MSG_END
            return {'file': output_file}

        # Processing the dump
        pgdump = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        dump_output = pgdump.communicate()[0]

        f = gzip.open(output_file, 'wb')
        f.write(dump_output)
        f.close()

        return {
            'file': output_file
        }

    @staticmethod
    def mongodb(settings, section):
        """MongoDB backup handler

        Should not be called directly
        """
        if not settings.has_option(section, 'database') or settings.get(section, 'database') == 'all':
            params = ['mongodump', '--out', folder]
        else:
            params = ['mongodump', '--db', settings.get(section, 'database'), '--out', folder]

        # Debug mode
        if debug:
            print DBG_MSG + "* MongoDB dump -> " + output_file + DBG_MSG_END
            return {'file': output_file}

        # Processing the dump
        # TODO

        return {
            'file': output_file
        }

#
#
#
class SyncBackup:
    """Synchronization class

    Allow to synchronize a file or a folder wiht another host.
    Can handle different protocols, like FTP, Rsync.
    It should also allow to dynamically crypt the data when sending it to the other host.
    """

    @staticmethod
    def process(settings, section, currentState):
        """Process the sync with the right protocol handler
        """
        if not settings.has_option(section, 'protocol'):
            return False
        handler = settings.get(section, 'protocol')
        if not handler in ['archive','copy','rsync','ftp']:
            return False

        # TODO : Manage group/file exclusion

        # List processed files
        files = []
        for x in currentState:
            if not x.has_key('ret') or not isinstance(x['ret'], dict):
                continue
            if not x['ret'].has_key('file') and not x['ret'].has_key('files'):
                continue
            file_section = x['section']
            file_group = '/'
            if settings.has_option(file_section, 'group'):
                file_group = settings.get(file_section, 'group')
            f = x['ret']['file'] if x['ret'].has_key('file') else x['ret']['files']
            if isinstance(f, str):
                files.append((f, file_section, file_group))
            if isinstance(f, list):
                files = files + [(x, file_section, file_group) for x in f]

        # Call the right handler
        syncMethod = getattr(SyncBackup, 'process' + handler.title())
        return syncMethod(settings, section, files)

    @staticmethod
    def processArchive(settings, section, seqfiles):
        """Archive handler

        The goal of that handler is to store the files in special folders and put a date on the copied files.
        The organisation of the files should be done thanks to the processed files and the "group" in their configuration.
        """

        # Get the "archive" folder (in 'default' section)
        archive_folder = settings.get('default', 'archive')

        # Get files organized in groups
        groups = {
            '/': []
        }
        for f in seqfiles:
            filename = f[0]
            group = f[2]
            if not groups.has_key(group):
                groups[group] = []
            groups[group].append( filename )

        # Copy the files in the different groups
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        for group in groups:
            for f in groups[group]:
                if not debug and (not os.path.exists(f) or not os.path.isfile(f)):
                    continue
                (filename, ext) = splitext(os.path.basename(f))
                dest = os.path.join(archive_folder, group, filename + '_' + date + ext)
                SyncBackup.copy(f, dest)

        # If we do not want to display it in the report
        return False

    @staticmethod
    def processCopy(settings, section, seqfiles):
        """Copy handler

        It is a basic handler which will just copy files
        """
        if not settings.has_option(section, 'dest'):
            return False
        dest = settings.get(section, 'dest')

        # Debug mode
        if debug:
            print DBG_MSG + "* Copy -> " + dest + "\n" + "\n".join([x[0] for x in seqfiles]) + DBG_MSG_END
            return True

        # Check
        if not os.path.exists(dest) or not os.path.is_dir(dest):
            return False

        # Performing the copy
        ret = subprocess.call(['cp'] + [x[0] for x in seqfiles] + [dest])
        return True

    @staticmethod
    def processRsync(settings, section, seqfiles):
        """Rsync handler

        An handler which can transfer through network using rsync
        """
        if not settings.has_option(section, 'host'):
            return False

        host = settings.get(section, 'host')

        # Debug mode
        if debug:
            print DBG_MSG + "* Rsync -> " + host + "\n  " + "\n  ".join([x[0] for x in seqfiles]) + DBG_MSG_END
            return True

        # Performing the copy
        ret = subprocess.call(['rsync', '-qt'] + [x[0] for x in seqfiles] + [host])
        return True

    @staticmethod
    def processFtp(settings, section, tuplefiles):
        """FTP handler

        When rsync is not available...
        """
        # TODO
        #import ftplib
        #session = ftplib.FTP('server.address.com','USERNAME','PASSWORD')
        #file = open('local_filename','rb')
        #session.storbinary('STOR dest_filename', file)
        #file.close()
        #session.quit()
        return False

    @staticmethod
    def copy(source, dest):
        # Debug mode
        if debug:
            print DBG_MSG + "* Copy " + source + " -> " + dest + DBG_MSG_END
            return True

        # Performing the copy
        ret = subprocess.call(['cp', source, dest])
        return True
#
#
#
class SvnBackup:
    """Subversion Backup class

    Allow to backup a SVN repository, with or without the 'svnadmin -hotcopy' folder
    """

    @staticmethod
    def process(settings, section):
        # Check the folder
        if not settings.has_option(section, 'folder'):
            return False
        folder = settings.get(section, 'folder')
        if not os.path.exists(folder):
            return False

        archive_format = 'tar.gz'
        archive_format_parameter = '--gzip' # --bzip2

        output_folder = settings.get('default', 'output')
        output_filename = settings.get(section, 'output') + '.' + archive_format
        output_file = os.path.join(output_folder, output_filename)

        # Create an hot-copy of the SVN in a temp folder
        svn_hot_copy = False
        svn_folder = folder
        if settings.has_option(section, 'hot') and (settings.get(section, 'hot').lower().strip() == 'true'):
            # Debug mode
            if debug:
                print DBG_MSG + "* Hotcopy archive SVN " + svn_folder + " -> " + output_file + DBG_MSG_END
                return True
            svn_hot_copy = True
            svn_folder = SvnBackup.hotcopy(folder, settings, section)

        # Parameters for the compression
        params = [
            'tar',
            '--ignore-failed-read',
            archive_format_parameter,
            '-cf',
            output_file,
            '-C',
            '/',
            svn_folder.lstrip('/')
        ]

        # Debug mode
        if debug:
            print DBG_MSG + "* Archive SVN " + svn_folder + " -> " + output_file + DBG_MSG_END
            return { 'file': output_file }

        # Processing the backup
        ret = subprocess.call(params)

        # Clean the temp SVN folder is needed
        if folder != svn_folder:
            if os.path.isdir(old_backup_item):
                safe_rmtree(old_backup_item, 1)
            else:
                os.remove(old_backup_item)

        #
        return {
            'file': output_file
        }

    @staticmethod
    def hotcopy(folder, settings, section):
        """Create an hotcopy of a SVN repository
        """
        output_folder = settings.get('default', 'output')
        dest_folder = os.path.join(output_folder, 'svn-hot-copy')
        err_code = subprocess.call([svnadmin, "hotcopy", folder, dest_folder, "--clean-logs"])
        if err_code != 0:
            return folder
        return dest_folder

    # For clearing away read-only directories (imported function)
    @staticmethod
    def safe_rmtree(dirname, retry=0):
        """Remove the tree at DIRNAME, making it writable first
        """
        def rmtree(dirname):
            SvnBackup.chmod_tree(dirname, 0666, 0666)
            shutil.rmtree(dirname)

        # Chmod recursively on a whole subtree
        def chmod_tree(path, mode, mask):
            for dirpath, dirs, files in os.walk(path):
                for name in dirs + files:
                    fullname = os.path.join(dirpath, name)
                    if not os.path.islink(fullname):
                        new_mode = (os.stat(fullname)[stat.ST_MODE] & ~mask) | mode
                        os.chmod(fullname, new_mode)
        # The function core
        if not os.path.exists(dirname):
            return

        if retry:
            for delay in (0.5, 1, 2, 4):
                try:
                    rmtree(dirname)
                    break
                except:
                    time.sleep(delay)
            else:
                rmtree(dirname)
        else:
            rmtree(dirname)

#
#
#
class ReportBackup:
    """Report class.
    """

    @staticmethod
    def process(settings, section):
        """Provide a report
        """
        if not settings.has_option(section, 'report'):
            return False
        ret = []
        handlers = settings.get(section, 'report').split(',')
        for handler in handlers:
            txt = False
            if handler == 'text' or handler.startswith('text:'):
                txt = ReportBackup.text(settings, section, handler)
            elif handler == 'disk':
                txt = ReportBackup.disk(settings, section)

            if not txt == False:
                ret.append(txt)
        return "\r\n".join(ret)

    @staticmethod
    def text(settings, section, handler='text'):
        """Text report processing
        """
        value = ''
        if handler == 'text':
            if not settings.has_option(section, 'value'):
                return False
            value = settings.get(section, 'value')
        else:
            key = handler[5:]
            if not settings.has_option(section, key):
                return False
            value = settings.get(section, key)

        value = getVars(value, settings, section)

        # Return a string with some tiny processing before
        return value.replace('\r\n', '\n').replace('\r', '\n').replace('\n_\n', '\n\n').strip('_').replace('\n', '\r\n')

    @staticmethod
    def disk(settings, section):
        """Disk usage report processing
        """
        # Original linux cmd: df / /home -hP | column -t
        if not settings.has_option(section, 'disks'):
            disks = ['/']
        else:
            disks = settings.get(section, 'disks').split(',')

        if len(disks) == 0:
            return False

        ret = "%-10s %8s %8s %8s %8s" % ( "Disk", "Size", "Used", "Avail", "Use%" )
        for disk in disks:
            try:
                status = os.statvfs(disk.strip(' '))
            except (OSError, IOError):
                print disk
                status = False

            if status == False or status.f_blocks == 0:
                continue

            free = status.f_bfree * status.f_frsize
            size = status.f_blocks * status.f_frsize
            avail = status.f_bavail * status.f_frsize
            used = (status.f_blocks - status.f_bfree) * status.f_frsize
            used_percent = str( round(100. * used / size, 1) ) + '%'

            ret += "\n%-10s %8s %8s %8s %8s" % ( disk, sizeof_fmt(size, ''), sizeof_fmt(used, ''), sizeof_fmt(avail, ''), used_percent )
        return ret

#
#
#
def dirBackup(settings, section):
    """Backup a classical folder
    """
    # Check the folder
    if not settings.has_option(section, 'folder'):
        return False
    folder = settings.get(section, 'folder')
    if not os.path.exists(folder):
        return False

    # Manage exclude list
    excludes = []
    if settings.has_option(section, 'exclude'):
        excludes = [x.strip(' ') for x in settings.get(section, 'exclude').split(',')]
    if len(excludes) == 0 and settings.has_option('default', 'exclude'):
        excludes = [x.strip(' ') for x in settings.get('default', 'exclude').split(',')]

    # Set archive format (improvement needed)
    archive_format = 'tar.gz'
    archive_format_parameter = '--gzip' # --bzip2

    # Set the output files/folder
    output_folder = settings.get('default', 'output')
    output_filename = settings.get(section, 'output') + '.' + archive_format
    output_file = os.path.join(output_folder, output_filename)

    # Processing params
    params = ['tar'] + [ ('--exclude="' + x + '"') for x in excludes ] + [
        '--ignore-failed-read',
        archive_format_parameter,
        '-cf',
        output_file,
        '-C',
        '/',
        folder.lstrip('/')
    ]

    if debug:
        print DBG_MSG + "* Backup folder " + folder + " -> " + output_file + DBG_MSG_END
        if len(excludes) > 0:
            print DBG_MSG + "  (exclude: " + ", ".join(excludes) + ")" + DBG_MSG_END
        return {'file': output_file}

    before_tar = datetime.datetime.now()

    os.chdir('/')
    ret = subprocess.call(params)

    # We can have the backup duration
    after_tar = datetime.datetime.now()

    # Return if we do not have to create the info file
    if (settings.has_option(section, 'info') and (settings.get(section, 'info').lower().strip() == 'true')):
        return {
            'file': output_file
        }

    # Generation of the info file
    info_file = output_file.replace('.'+archive_format, '.info.txt')
    uname = os.uname()
    hostname = uname[0] + '@' + uname[1]
    md5_hash = generate_file_md5(output_folder, output_file)

    file_content = '''
Directory backup :
 Date : ''' + before_tar.strftime("%Y-%m-%d %H:%M") + '''
 User : ''' + hostname + '''
 Folder : ''' + folder + '''
 MD5 : ''' + md5_hash + '''

File list :
'''
    # TODO
    '''
    find "$dir" -ls | grep -v ".svn" >> "$txt"

    if [ -d "$dir/.svn" ]; then
        echo >> "$txt"
        echo "SVN Status" >> "$txt"
        echo >> "$txt"
        svn status -uv "$dir" >> "$txt"
    fi
    '''

    return {
        'files': [output_file, info_file]
    }

#
#
#
def generate_file_md5(rootdir, filename, blocksize=2**20):
    import hashlib
    m = hashlib.md5()
    try:
        with open( os.path.join(rootdir, filename) , "rb" ) as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                m.update( buf )
    except:
        return '-- Hash Error --'
    return m.hexdigest()

#
#
#
def cleanBackup(settings, section):
    """Clean Backup
    """

    # TODO
    """
# Original code from "hdbackup"
BACKUP_DIR="/home/backup/test/"
DAYS="5"
LOCALDAYS="2"
LOCALMONTH="32"

# SPARSING
# [archive]_YYYY-MM-DD.[ext]
# ctime +6 => fichiers d'il y a 6 jours
find $BACKUP_DIR -name "*_[2-9][0-9][0-9][0-9]-[01][0-9]-[1-3][0-9].*" -daystart -mtime +$DAYS -exec rm {} \;
find $BACKUP_DIR -name "*_[2-9][0-9][0-9][0-9]-[01][0-9]-0[2-9].*" -daystart -mtime +$DAYS -exec rm {} \;

find $BACKUP_DIR -name "local.svn_[2-9][0-9][0-9][0-9]-[01][0-9]-[1-3][0-9].*" -daystart -mtime +$LOCALDAYS -exec rm {} \;
find $BACKUP_DIR -name "local.svn_[2-9][0-9][0-9][0-9]-[01][0-9]-0[0-9].*" -daystart -mtime +$LOCALDAYS -exec rm {} \;
find $BACKUP_DIR -name "local.svn_[2-9][0-9][0-9][0-9]-[01][0-9]-01.*" -daystart -mtime +$LOCALMONTH -exec rm {} \;
    """

    return False

#
#
#
def dpkgBackup(settings, section):
    """Dpkg Backup

    It will generate a file with all installed packages.
    This function is related to linux system using APT (Debian/Ubuntu)
    """
    # Check the output variable
    if not settings.has_option(section, 'output'):
        return False
    output = settings.get(section, 'output')

    if debug:
        print DBG_MSG + "* Create DPKG selection -> " + output + DBG_MSG_END
        return True

    # Call dpkg with pip support to write the output into a file
    dpkg = subprocess.Popen(['dpkg', '--get-selections'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dpkg_output = dpkg.communicate()[0]

    f = open(output, 'w')
    f.write(dpkg_output)
    f.close()

    return True

#
#
#
def processBackup(settings, section, result=None):
    """Processing function

    It read the type of the section and call the right handler (dir, svn, db...)
    """
    if not settings.has_option(section, 'type'):
        return 0

    t = settings.get(section, 'type')
    if t == 'folder' or t == 'dir':
        return dirBackup(settings, section)
    elif t == 'sync':
        return SyncBackup.process(settings, section, result)
    elif t == 'db' or t == 'database':
        return DatabaseBackup.process(settings, section)
    elif t == 'svn':
        return SvnBackup.process(settings, section)
    elif t == 'report':
        return ReportBackup.process(settings, section)
    elif t == 'clean':
        return cleanBackup(settings, section)
    elif t == 'dpkg':
        return dpkgBackup(settings, section)
    return 0

#
#
#
def folderSize(folder, suffix='B'):
    total_size = 0
    for root, dirs, files in os.walk(folder):
        total_size += sum(os.path.getsize(os.path.join(root, name)) for name in files)
    return sizeof_fmt(total_size, suffix)

#
#
#
def treeSize(folder, suffix='B'):
    ret = ""
    l = len(folder)
    for root, dirs, files in os.walk(folder):
        ret += folder if folder == root else " " + root[l:]
        s = sum(os.path.getsize(os.path.join(root, name)) for name in files)
        if s > 0:
            ret += " [" + sizeof_fmt(s) + "]"
        if len(files) > 0:
            ret += " %d files" % len(files)
        ret += "\n"
    return ret.strip("\n")

#
#
#
def sizeof_fmt(num, suffix='B'):
    """Display function: Nice file size
    """
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)

#
#
#
def pretty_timedelta(data):
    """Display function: Nice time delta
    """
    if isinstance(data, datetime.timedelta):
        seconds = abs(int(data.total_seconds()))
    else:
        seconds = int(data)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%dd%dh%dm%ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh%dm%ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm%ds' % (minutes, seconds)
    return '%ds' % (seconds,)

#
#
#
def splitext(path):
    for ext in ['.tar.gz', '.tar.bz2']:
        if path.endswith(ext):
            return path[:-len(ext)], path[-len(ext):]
    return os.path.splitext(path)

#
#
#
def getTextResult(settings, section, data):
    """Prepare some text for the final report
    """
    if not settings.has_option(section, 'type'):
        return 0

    t = settings.get(section, 'type')
    if t == 'report':
        return data['ret']
    elif t == 'dpkg':
        return ""

    if not t in ('folder', 'dir', 'db', 'database', 'svn'):
        return 0

    # Name
    name = ""
    if settings.has_option(section, 'name'):
        name = settings.get(section, 'name')
    elif settings.has_option(section, 'folder'):
        name = settings.get(section, 'folder')

    # Duration
    duration = " (" + pretty_timedelta(data['end'] - data['start']) + ")"

    # Size
    size = ""
    if isinstance(data['ret'], dict) and (data['ret'].has_key('file') or data['ret'].has_key('files')):
        files = data['ret']['file'] if data['ret'].has_key('file') else data['ret']['files']
        totalsize = 0
        if isinstance(files, str):
            files = [files]
        for f in files:
            if os.path.exists(f) and os.path.isfile(f):
                statinfo = os.stat(f)
                totalsize += statinfo.st_size
        if totalsize > 0:
            size = " [" + sizeof_fmt(totalsize) + "]"

    # Processing
    if t == 'folder' or t == 'dir':
        return "Backup folder \"" + name + "\"" + duration + size
    elif t == 'db' or t == 'database':
        return "Backup " + name + " database" + duration + size
    elif t == 'svn':
        return "Backup SVN repository \"" + name + "\"" + duration + size
    return 0

#
#
#
def getVars(text, settings, section):
    """Replace the special tags by their corresponding variable
    """

    def getVar(key, settings, section):
        """Get variable content for text report
        """
        # Formatted date time
        if key == 'now':
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # Direct link to datetime values
        if key in ('year','month','day','hour','minute','second'):
            return str(getattr(datetime.datetime.now(), key))
        if key.startswith('size:') or key.startswith('tree:'):
            folder = key[5:]
            if folder == 'output':
                folder = settings.get('default', 'output')
            elif folder == 'archive':
                folder = settings.get('default', 'archive')
            if key.startswith('size:'):
                return folderSize(folder)
            return treeSize(folder)
        return ""

    #
    reg = re.compile(r'{([\s\w\.\-\:\%]+)}', re.UNICODE)
    for match in reg.finditer(text):
        text = text.replace('{'+match.group(1)+'}', getVar(match.group(1), settings, section))
    return text

#
#
#
def main(configFile = None):
    """Main function of the program

    It will read the configuration file and process it.
    It also retrieve the return of the processing to display the report at the end.
    """
    if configFile == None:
        configFile = '/etc/distbackup.cfg'

    result = []
    settings = ConfigParser.ConfigParser()
    if settings.read(configFile) == []:
        return False
    for section in settings.sections():
        if section == 'default':
            continue
        date_start = datetime.datetime.now()

        # Perform the action
        ret = processBackup(settings, section, result)

        date_stop = datetime.datetime.now()

        if ret != False and ret != 0:
            data = {
                'start': date_start,
                'end': date_stop,
                'section': section,
                'ret': ret
            }
            display = getTextResult(settings, section, data)
            if display != False and display != "" and display != 0:
                print display
            result.append( data )
    return result

#
# Process arguments
#
try:
    optlist, args = getopt.getopt(sys.argv[1:], 'c:', ['debug'])
except getopt.GetoptError as err:
    print str(err)
    sys.exit(2)

# Configuration variables
configFile = None
debug = False
DBG_MSG = '\033[95m'
DBG_MSG_END = '\033[0m'

# Read parameters
for o, a in optlist:
    if o == '-c':
        configFile = a
    elif o == "--debug":
        debug = True

#
# Do the backup stuff
#
result = main(configFile)

if result == False:
    sys.stderr.write("Configuration not found (" + configFile + ")\n")
    sys.stderr.flush()
    sys.exit(2)

if len(result) == 0:
    sys.stderr.write("Nothing to do\n")
    sys.stderr.flush()
    sys.exit(1)