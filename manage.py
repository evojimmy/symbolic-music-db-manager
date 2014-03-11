#!/usr/bin/env python

"""
Score database manager.
"""

import sys, os, shutil, tempfile, subprocess

USAGE = """
[Usage] manage.py help ACTION
        manage.py list
        manage.py checkout LISTFILE DESTINATION [SEPARATOR="_"]
        manage.py check_integrity [ID]...
        manage.py listen ID COMMAND
        manage.py view   ID
        manage.py export ID  [DESTINATION="$ID.pdf"]
        manage.py export_all DESTINATION [KEEP_TEMP_FILES="discard"(or "keep")]
"""
USAGE_MORE = {}
USAGE_MORE['list'] = """[Usage] manage.py list

    List all IDs of excerpts saved in this database.
"""
USAGE_MORE['checkout'] = """[Usage] manage.py checkout LISTFILE DESTINATION [SEPARATOR="_"]

    Check out all related excerpts as defined by LISTFILE.

    LISTFILE should be a white-space-separated file.
    DESTINATION should not exist. It will be automatically created.

    Example: LISTFILE contains "1 2 123". SEPARATOR is "_"
             These files will be checked out: 1_1, 1_2, 2_1_2, 123_1, etc.
"""
USAGE_MORE['check_integrity'] = """[Usage] manage.py check_integrity [ID]...

    Run through Lilypond to find out broken files in database. Broken
    files are invalid in Lilypond format, without PDF output, or without
    MIDI output.

    ID is a list of parameters. Both "123" and "123.ly" are valid IDs.
    If ID is omitted, manage.py will check all files.
"""
USAGE_MORE['listen'] = """[Usage] manage.py listen ID COMMAND

    Call COMMAND to play midi generated by listen. MIDI filename is
    automatically generated and appended to COMMAND.

    Example: manage.py listen 123 "aplaymidi --port=129:0"
"""
USAGE_MORE['view'] = """[Usage] manage.py view ID

    Generate PDF and open it in system's preferred program.
"""
USAGE_MORE['export'] = """[Usage] manage.py export ID [DESTINATION="$ID.pdf"]

    Export as PDF and save it to DESTINATION.
"""
USAGE_MORE['export_all'] = """[Usage] manage.py export_all DESTINATION [KEEP_TEMP_FILES="discard"(or "keep")]

    Export all excerpts as PDF in temporary directory, and concatenate
    them into DESTINATION file.

    If KEEP_TEMP_FILES is "keep", the temporary directory will not be
    deleted after PDF concatenation. Useful for generating individual
    PDFs and MIDIs.
"""

base_path = os.path.realpath(os.path.dirname(__file__))
data_path = base_path + os.sep + 'data'
temp_path = None

def main():
    actions = ['help', 'list', 'checkout', 'check_integrity'
               ,'listen', 'view', 'export', 'export_all']
    argv = sys.argv
    if len(argv) < 2:
        manage_works.help()

    action = argv[1]
    if action not in actions:
        manage_works.help()

    getattr(manage_works, action)(*sys.argv[2:])

class manage_works(object):
    @staticmethod
    def list(*args):
        l = _files()
        print('\n'.join(l))
        print('')
        print('Total excerpts: %s' % len(l))
    @staticmethod
    def help(action='', *args):
        if action in USAGE_MORE:
            raise TypeError(USAGE_MORE[action])
        else:
            raise TypeError(USAGE)
    @staticmethod
    def checkout(listfile, dest, seperator='_'):
        # check for any dirt
        with open(listfile) as f:
            id_list = f.read().strip().split()
        id_list.sort()
        dest = os.path.realpath(dest)
        if base_path.startswith(dest):
            raise ValueError('manage.py checkout: cannot check out to subfolder of myself')
        if os.path.exists(dest):
            raise ValueError('manage.py checkout: cannot check out to an exist folder')
        os.makedirs(dest)
        dest_data = dest + os.sep + 'data'
        os.makedirs(dest_data)

        # do things
        files = _files()
        for id_ in id_list:
            checked_out = False
            for f in os.listdir(data_path):
                if f.endswith('.ly') and f.startswith(id_ + seperator):
                    shutil.copy(data_path + os.sep + os.path.basename(f),
                                dest_data)
                    checked_out = True
            if not checked_out:
                print('warning: No files found for %s' % id_)

        shutil.copy(base_path + os.sep + 'manage.py', dest)
        shutil.copy(base_path + os.sep + 'README.md', dest)
        print('Done.')
    @staticmethod
    def check_integrity(*args):
        if len(args) == 0:
            l = _files()
        else:
            l = list(map(_id_cleaner, args))
        output_arg = '--output=' + temp_path + os.sep + 'temp'
        brokens = []
        for index, f in enumerate(l):
            sys.stdout.write('%s Checking %s... ' % (_a_of_b(index+1, len(l)), f))
            sys.stdout.flush()
            try:
                os.unlink(temp_path + os.sep + 'temp.pdf')
            except OSError:
                pass
            try:
                os.unlink(temp_path + os.sep + 'temp.midi')
            except OSError:
                pass
            try:
                subprocess.check_call(['lilypond', '--silent', output_arg, data_path + os.sep + f], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                print('Broken: invalid Lilypond format.')
                brokens.append(f + '.ly')
            else:
                if not os.path.isfile(temp_path + os.sep + 'temp.pdf'):
                    print('Broken: no PDF output.')
                elif not os.path.isfile(temp_path + os.sep + 'temp.midi'):
                    print('Broken: no MIDI output.')
                else:
                    print('Good.')
        print('')
        if len(brokens) > 0:
            print('There are broken Lilypond files: %s' % ' '.join(brokens))
        else:
            print('All is well.')
    @staticmethod
    def view(id_, *args):
        id_ = _id_cleaner(id_)
        output_arg = '--output=' + temp_path + os.sep + 'temp'
        data_file = data_path + os.sep + id_ + '.ly'
        if not os.path.isfile(data_file):
            raise ValueError('File %s.ly not exist.' % id_)
        try:
            print('Generating score...')
            subprocess.check_call(['lilypond', '--silent', output_arg, data_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('Error when calling Lilypond. File might broken.')
        _open(temp_path + os.sep + 'temp.pdf')
        sys.exit(0)
    @staticmethod
    def export(id_, outfile=None):
        id_ = _id_cleaner(id_)
        if outfile is None:
            outfile = id_
        if not outfile.endswith('.pdf'):
            outfile = outfile + '.pdf'
        outfile = os.path.realpath(outfile)
        if os.path.exists(outfile):
            raise ValueError('File %s exists. Exiting...' % outfile)
        output_arg = '--output=' + temp_path + os.sep + 'temp'
        data_file = data_path + os.sep + id_ + '.ly'
        if not os.path.isfile(data_file):
            raise ValueError('File %s.ly not exist.' % id_)
        try:
            print('Generating score %s...' % id_)
            subprocess.check_call(['lilypond', '--silent', output_arg, data_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('Error when calling Lilypond. File might broken.')
        shutil.copy(temp_path + os.sep + 'temp.pdf', outfile)
        print('Done: %s' % outfile)

    @staticmethod
    def export_all(outfile, keep_temp_files="discard"):
        if not outfile.endswith('.pdf'):
            outfile = outfile + '.pdf'
        outfile = os.path.realpath(outfile)
        if os.path.exists(outfile):
            raise ValueError('File %s exists. Exiting...' % outfile)
        try:
            subprocess.check_call('pdftk', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('Please install pdftk.')

        l = _files()
        for index, i in enumerate(l):
            output_arg = '--output=' + temp_path + os.sep + i
            data_file = data_path + os.sep + i + '.ly'
            try:
                print('%s Generating score %s...' % (_a_of_b(index+1, len(l)), i))
                subprocess.check_call(['lilypond', '--silent', output_arg, data_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                raise RuntimeError('Error when calling Lilypond. File might broken.')
        files = list(map(lambda f: temp_path + os.sep + f + '.pdf', l))
        try:
            subprocess.check_call('pdftk ' + ' '.join(files) + ' cat output ' + outfile, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print('Error concatenating pdf files. Individual pdf files are preserved in %s' % temp_path)
            sys.exit(0)
        print('Done: %s' % outfile)
        if keep_temp_files == 'keep':
            print('Temp file directory: %s' % temp_path)
            sys.exit(0)
    @staticmethod
    def listen(id_, command):
        id_ = _id_cleaner(id_)
        output_arg = '--output=' + temp_path + os.sep + 'temp'
        data_file = data_path + os.sep + id_ + '.ly'
        if not os.path.isfile(data_file):
            raise ValueError('File %s.ly not exist.' % id_)
        try:
            print('Generating midi %s...' % id_)
            subprocess.check_call(['lilypond', '--silent', output_arg, data_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('Error when calling Lilypond. File might broken.')
        print('Playing...')
        subprocess.check_call(command + ' ' + temp_path + os.sep + 'temp.midi', shell=True)

def _files():
    l = list(filter(lambda f: f.endswith('ly'), os.listdir(data_path)))
    l = list(map(lambda f: f[0:-3], l))
    l.sort()
    return l
def _open(filepath):
    # http://stackoverflow.com/questions/434597/open-document-with-default-application-in-python
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))
    else:
        raise RuntimeError('Unidentified system: ' % os.name)

_id_cleaner = lambda i: i[0:-3] if i.endswith('.ly') else i

def _a_of_b(a, b):
    l = len(str(b))
    s = "[ %" + str(l) + "d/%s ]"
    return s % (a, b)

if __name__ == '__main__':
    temp_path = tempfile.mkdtemp()
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted. Exiting...')
    except Exception as e:
        print(e)
    shutil.rmtree(temp_path)
else:
    raise ImportError("Score database manager forbids import.")
