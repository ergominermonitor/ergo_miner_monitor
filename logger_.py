import logging
import os
import sys
import time
from colorama import Fore, Style
from helper_functions import cprint, file_exist, get_current_time, trace_error


def check_path(logfile='logfile.txt', sole_output=False, debug=False, to_log=False, q=''):
    """Returns the path of the logfile
       The output won't be logged because start_logging() starts after check_path and check_filemode are called"""
    path_to_file = ''
    try:
        #  If the script is running from a python console.
        if '.py' in sys.argv[0].split('\\')[0]:
            path = os.path.abspath(os.path.dirname(__file__))
            if debug and sole_output:
                cprint(f'check_path(): sys.argv {sys.argv}', to_log=to_log, q=q)
                suffix = sys.argv[0].split("\\")[0].split('.')[1]
                script = sys.argv[0].split("\\")[0]
                cprint(f'check_path(): The program is probably running from a {suffix} script named {script}',
                       to_log=to_log, q=q)
                cprint(f'check_path(): os.path.abspath(os.path.dirname(__file__)): '
                       f'{os.path.abspath(os.path.dirname(__file__))}', to_log=to_log, q=q)
            if '\\' in path:
                name = path.split('\\')
                path_to_file = '\\'.join(name)
                if debug and sole_output:
                    cprint(f"check_path(): list of the path: {name}", to_log=to_log, q=q)
            elif '/' in path:
                name = path.split('/')
                path_to_file = '/'.join(name)
                if debug and sole_output:
                    cprint(f"check_path(): list of the path: {name}", to_log=to_log, q=q)
            elif r"\\" in path:
                name = path.split(r'\\')
                path_to_file = r'\\'.join(name)
                if debug and sole_output:
                    cprint(f"check_path(): list of the path: {name}", to_log=to_log, q=q)
            path_to_file = f"{path_to_file}\\{logfile}"
            # path_to_file = pathlib.Path(os.path.join(path_to_file,logfile))
            if debug and sole_output:
                cprint(f'check_path(): path_to_file: {path_to_file}', to_log=to_log, q=q)
            return path_to_file
        else:
            #  If the script is running as an exe.
            if debug and sole_output:
                suffix = sys.argv[0].split("\\")[-1].split('.')[-1]
                exe = sys.argv[0].split("\\")[-1]
                cprint(f'check_path(): The program is probably running from a {suffix} named: {exe}', to_log=to_log,
                       q=q)
            path = sys.argv[0].split('\\')
            path = '\\'.join(path[:-1])
            if debug and sole_output:
                cprint(f'check_path(): sys.argv path: {sys.argv}', to_log=to_log, q=q)
            if debug and sole_output:
                cprint(f'check_path(): path: {path}', to_log=to_log, q=q)
            if '\\' in path:
                name = path.split('\\')
                path_to_file = '\\'.join(name)
                if debug and sole_output:
                    cprint(f"check_path(): list of the path: {name}", to_log=to_log, q=q)
            elif '/' in path:
                name = path.split('/')
                path_to_file = '/'.join(name)
                if debug and sole_output:
                    cprint(f"check_path(): list of the path: {name}", to_log=to_log, q=q)
            elif r"\\" in path:
                name = path.split(r'\\')
                path_to_file = r'\\'.join(name)
                if debug and sole_output:
                    cprint(path_to_file, to_log=to_log, q=q)
                    cprint(f"check_path(): list of the path: {name}", to_log=to_log, q=q)
            path_to_file = f"{path_to_file}\\{logfile}"
            # path_to_file = pathlib.Path(os.path.join(path_to_file, logfile))
            if debug and sole_output:
                cprint(f'check_path(): path_to_file: {path_to_file}', to_log=to_log, q=q)
            return path_to_file
    except Exception as err:
        cprint(f"check_path(): error in checking path: {Fore.RED}{err}{Style.RESET_ALL}", to_log=to_log, q=q)


def check_filemode(path='', logfile='logfile.txt', debug=False, sole_output=False, to_log=True, q=''):
    """Checks if there is a log file.
       Sole_output is True only in if __name__ == "__main__"
       so as not to have duplicates cpinted from other multi processes.
       The output won't be logged because start_logging() starts after check_path and check_filemode are called"""
    mode_write = 'w'
    mode_append = 'a'
    try:
        path_to_file = path
        # path_to_file = os.path.join(path_to_file)
        # cprint(path_to_file, to_log=to_log, q=q)
        # subprocess.Popen(os.path.join(path_to_file))
        if file_exist(logfile, to_log=to_log, q=q, sole_output=sole_output, debug=debug):
            if sole_output:
                cprint(f'The {logfile} exists.', to_log=to_log, q=q)
            if debug and sole_output:
                cprint(f'check_filemode(): Path_to_file: {path_to_file}', to_log=to_log, q=q)
            log_mode = mode_append
            if debug and sole_output:
                cprint(f'log_mode: {log_mode}', to_log=to_log, q=q)
            return log_mode
        else:
            if sole_output:
                cprint(f'The {logfile} does not exists.'
                       f'\n{get_current_time()}A new one will be created.', to_log=to_log, q=q)
            time.sleep(0.001)
            log_mode = mode_write
            if debug and sole_output:
                cprint(f'log_mode: {log_mode}', to_log=to_log, q=q)
            return log_mode
    except Exception as err:
        if sole_output:
            cprint(f'The {logfile} does not exists.'
                   f'\n{get_current_time()}A new one will be created.', to_log=to_log, q=q)
        time.sleep(0.001)
        log_mode = mode_write
        if debug and sole_output:
            cprint(f'Log_mode: {log_mode}: Error: {err}', to_log=to_log)
        return log_mode


def start_logging(path_to_file, log_mode):
    """Starts logging. Force must be true, otherwise no logging will be done.
    https://stackoverflow.com/questions/20240464/python-logging-file-is-not-working-when-using-logging-basicconfig"""

    if not path_to_file and log_mode:
        logging.basicConfig(level=logging.INFO,
                            format=f'%(message)s')
    try:
        logging.basicConfig(level=logging.INFO,
                            format=f'%(message)s',
                            filename=path_to_file,
                            filemode=log_mode,
                            force=True)
        # cprint(f'Logging started.')
        # time.sleep(0.01)
    except Exception as err:
        trace_error()  # TODO: To save to a file errors.txt
        cprint(f"start_logging()> {err}")
