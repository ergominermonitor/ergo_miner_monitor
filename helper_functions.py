import argparse, ctypes
import contextlib
import datetime
import json
import logging
import os
import pathlib
import platform
import random
import re
import subprocess
import sys
import time
import traceback

import psutil
from colorama import Style, Fore, Back

headers_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
    "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36,"
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.53",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.62 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.115 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.47",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.33",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.39",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36 OPR/86.0.4363.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36 Edg/101.0.1210.39",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.30"]


def headers(debug=False):
    """Picks and returns a random user agent from the list"""
    header = {'User-Agent': random.choice(headers_list)}
    if debug:
        cprint(f'Random header: {header}')
    return header


def str2bool(v):
    """
    Convert a string to a boolean argument
    https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    """
    if isinstance(v, bool):
        return v
    elif isinstance(v, int):
        if v == 1:
            return True
        elif v == 0:
            return False
    elif v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def trace_error(to_log=False, q=None, time=True, to_print_error=True):
    """
    The function traces the exceptions by printing and logging the error using cprint().

    :param to_log: Boolean - To log the output
    :param q: The Queue object
    :param time: To print/log time (Boolean)
    :param to_print_error: Boolean - If true, prints and logs. Else, its logs the errors in a separate txt file
    :return: None

    See also:
    # https://docs.python.org/3/library/traceback.html#traceback-examples
    """
    # exc_type, exc_value, exc_traceback = sys.exc_info()  # All the info from the exception
    formatted_lines = traceback.format_exc().splitlines()
    json_data = ''
    for line in formatted_lines:
        if to_print_error:
            cprint(line, to_log=to_log, q=q, time=time)
        else:
            if file_exist('errors.txt', debug=False):
                with open('errors.txt', 'r+', encoding='utf-8') as file:
                    json_data = json.load(file)
                    if len(json_data) == 0:  # To avoid empty string in the text file
                        json_data = line
                    else:
                        json_data.update(line)
                with open('errors.txt', 'w+', encoding='utf-8') as file:
                    json.dump(json_data, file, indent=4)
            else:
                with open('errors.txt', 'w+', encoding='utf-8') as file:
                    json_data.update(line)
                    json.dump(json_data, file, indent=4)


def is_admin():
    try:
        return str2bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (ctypes.WinError(), BaseException) as err:
        print(err)


def prompt_to_acquire_admin_rights_and_exit():
    """https://stackoverflow.com/questions/130763/request-uac-elevation-from-within-a-python-script """
    if is_admin():
        pass
    else:
        # Re-run the program with admin rights and exit the current instance.
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                            " ".join(sys.argv[1:]), None, 1)  # Join sys.argv arguments with a space
        sys.exit()


def exe_name_of_miner(processName):
    """Adds '.exe' if there is not any at the end of the given name."""
    if '.exe' not in processName:
        processname = processName + '.exe'
        return processname
    else:
        return processName


def get_name_of_current_exe():
    """Returns the name of the current process. For example: internet.exe"""
    path = sys.argv[0]
    if platform.system() == 'Windows':
        if '\\' in path:
            name = path.split('\\')[-1]
            return name
        elif '/' in path:
            name = path.split('/')[-1]
            return name


def bat_name_of_miner(batname):
    """Adds '.bat' if there is not any at the end of the given name."""
    if '.exe' in batname:
        batname = batname.split('.exe')
        batname = batname[0]
        if '.bat' not in batname:
            batname = batname + '.bat'
            return batname
    if '.bat' not in batname:
        batname = batname + '.bat'
        return batname
    else:
        return batname


def get_current_time():
    time_now = datetime.datetime.now()
    dt = str(time_now.strftime("%d-%m-%Y %H:%M:%S")) + f'.{Fore.LIGHTBLACK_EX}{str(round(time_now.microsecond))[:4]}' \
                                                       f'{Style.RESET_ALL}'
    dt = f"[{dt}]\t"
    return dt


class DummyColorama:
    """A class to temporarily disable Colorama Fore and Style in order to log to a file
       https://stackoverflow.com/questions/63100603/globally-turn-off-colorama-colour-codes"""
    BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = LIGHTBLACK_EX = \
        LIGHTRED_EX = LIGHTGREEN_EX = LIGHTYELLOW_EX = LIGHTBLUE_EX = LIGHTMAGENTA_EX = LIGHTCYAN_EX = LIGHTWHITE_EX = \
        RESET_ALL = ""


@contextlib.contextmanager
def without_colorama():
    global Style
    saved_Style, Style = Style, DummyColorama
    global Fore
    saved_Fore, Fore = Fore, DummyColorama
    global Back
    saved_Back, Back = Back, DummyColorama
    yield
    Fore = saved_Fore
    Style = saved_Style
    Back = saved_Back


def strip_ansi_characters(text=''):
    """https://stackoverflow.com/questions/48782529/exclude-ansi-escape-sequences-from-output-log-file"""
    try:
        ansi_re = re.compile(r'\x1b\[[0-9;]*m')
        return re.sub(ansi_re, '', text)
    except re.error as err:
        print(err)


def file_exist(name, debug=False, to_log=True, q='', sole_output=False):
    # path = pathlib.Path(os.path.join(os.path.abspath(os.path.dirname(__file__)), name))
    try:
        path = sys.argv[0].split('\\')
        path = '\\'.join(path[:-1])
        # path = 'C:\\'
        path = pathlib.Path(os.path.join(path, name))
        if debug and sole_output:
            cprint(f'file_exist(): {path}', to_log=to_log, q=q)
        if path.exists():
            return True
        else:
            return False
    except FileNotFoundError as err:
        cprint(f'A problem occured with the path to {name}', to_log=to_log, q=q)
        if debug:
            cprint(f'A problem occured with the path to {name}.\n Error: {err}', to_log=to_log, q=q)


def get_current_time_without_color():
    with without_colorama():
        time_now = datetime.now()
        dt = str(time_now.strftime("%d-%m-%Y %H:%M:%S")) + \
             f'.{Fore.LIGHTBLACK_EX}{str(round(time_now.microsecond))[:4]}{Style.RESET_ALL}'
        dt = f"[{dt}]\t"
        return dt


def cprint(text, to_log=False, q=None, time=True):
    """Prints and logs the printed text"""
    text = str(text)  # Be sure that text is a string.
    if time:
        if q == "":
            print(f'{get_current_time()}{text} >> Queue not detected')
            if to_log:
                with without_colorama():
                    logging.info(f'{get_current_time()}{strip_ansi_characters(text)}')
        elif not q:
            print(f'{get_current_time()}{text} >> Queue not detected')
            if to_log:
                with without_colorama():
                    logging.info(f'{get_current_time()}{strip_ansi_characters(text)}')
        elif q:
            q.put(f'{get_current_time()}{text}')
            if to_log:
                with without_colorama():
                    logging.info(f'{get_current_time()}{strip_ansi_characters(text)}')
    elif not time:
        if q == "":
            print(f'{text} >> Queue not detected')
            if to_log:
                with without_colorama():
                    logging.info(f'{strip_ansi_characters(text)}')
        elif not q:
            print(f'{text} >> Queue not detected')
            if to_log:
                with without_colorama():
                    logging.info(f'{strip_ansi_characters(text)}')
        elif q:
            q.put(f'{text}')
            if to_log:
                with without_colorama():
                    logging.info(f'{strip_ansi_characters(text)}')


def restart_whole_process(to_log=True, q=""):
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                            " ".join(sys.argv[1:]), None, 1)  # Join sys.argv arguments with a space
    except (BaseException, SystemExit, RuntimeError, ctypes.FormatError, ctypes.WinError,
            ctypes.ArgumentError) as err:  # (ctypes.GetLastError())
        cprint(f"restart_whole_process>Error: {err}", to_log=to_log, q=q)
        time.sleep(2)
    finally:
        cprint("Exiting now..", to_log=to_log, q=q)
        sys.exit()


process_list = []


def checkIfProcessRunning(processName, to_print=False, to_log=True, Verbose=True, q=''):
    """
    Check if there is any running process that contains the given name processName.
    """
    global process_list
    process_list = []  # Clear the list
    # Iterate over all the running process
    for process in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in process.name().lower():
                process_info = process.as_dict(attrs=['name', 'pid'])
                process_list.append(process_info)
                if to_print:
                    if Verbose:
                        cprint(f">>>{Fore.LIGHTYELLOW_EX}{process.name()} "
                               f": {process.pid} {Style.RESET_ALL} "
                               f"found and added to the process list successfully.", to_log=to_log, q=q)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
            cprint(f"Error in finding the process due to {err}", to_log=to_log, q=q)

    if len(process_list) == 0:
        return False
    elif len(process_list) != 0:
        return True


def findAllProcessesRunning(processName, to_print=False, to_log=True, Verbose=True, q=''):
    """
    Returns a list with dictionaries containings all the pids with the same name. If no process is found,
    it returns an empty list.
    :param processName: The name of the process to be searched
    :param to_print: Boolean
    :param to_log: Boolean
    :param Verbose:
    :param q: The Queue object.
    :return: list with dictionaries or empty list
    """
    processes_list = []  # Clear the list
    # Iterate over all the running process
    for process in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in process.name().lower():
                process_info = process.as_dict(attrs=['name', 'pid'])
                processes_list.append(process_info)
                if to_print:
                    if Verbose:
                        cprint(f">>>{Fore.LIGHTYELLOW_EX}{process.name()} "
                               f": {process.pid} {Style.RESET_ALL} "
                               f"found and added to the process list successfully.", to_log=to_log, q=q)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
            cprint(f"Error in finding the process due to {err}", to_log=to_log, q=q)

    if len(processes_list) == 0:
        return []
    elif len(processes_list) != 0:
        return processes_list


def killiftheprocess(processName, to_log=True, q=''):
    """
    Checking if there is a process in process_list and kills the name that matches
    exactly the given name of the Process. Adds '.exe' if there is not any at the end of the given name.
    """
    if len(process_list) == 0:
        checkIfProcessRunning(processName, to_log=to_log, q=q)
        # TODO: modify this function to include findAllProcessesRunning()
    try:
        processName = exe_name_of_miner(processName)
        for process_dict in process_list:
            if process_dict['name'].lower() == processName.lower():
                process_name = process_dict['name']
                process_pid = process_dict['pid']
                os.kill(process_pid, 9)
                cprint(f'>>>{Fore.GREEN}The process {process_name} '
                       f': {process_pid} '
                       f'killed successfully{Style.RESET_ALL}', to_log=to_log, q=q)
    except Exception as err:
        cprint(f"Error in killing the {processName} process: {err}", to_log=to_log, q=q)


def countdown_to_restart_whole_process(process_main_loop_psutil, to_log, q):
    cprint(f"{Fore.LIGHTRED_EX}A internal process is not running.{Style.RESET_ALL}", to_log=to_log, q=q)
    cprint(f"{Fore.LIGHTRED_EX}Restarting the script.{Style.RESET_ALL}", to_log=to_log, q=q)
    try:
        process_main_loop_psutil.suspend()  # So as not to kill the new process
    except psutil.Error as err:
        cprint(f"countdown_to_restart_whole_process>Error: {err}", to_log=to_log, q=q)
        time.sleep(3)
    # https://stackoverflow.com/questions/5852981/python-how-do-i-display-a-timer-in-a-terminal
    for remaining in range(5, 0, -1):
        # sys.stdout.write("\r")
        cprint(f"{remaining:2d} seconds until restart.", to_log=to_log, q=q)
        # sys.stdout.flush()
        time.sleep(1)
    restart_whole_process()


def start_the_miner(filepath="", bat_file='ergo.bat', debug=False, to_log=True, q=''):
    """Starts the bat file of the miner from the given filepath"""
    # https://queirozf.com/entries/python-3-subprocess-examples
    if filepath == "":
        filepath = sys.argv[0].split('\\')
        filepath = '\\'.join(filepath[:-1])
    if debug:
        cprint(f'start_the_miner(): filepath: {filepath}', to_log=to_log, q=q)
    try:
        bat = bat_name_of_miner(bat_file)
        path_to_miner = os.path.join(filepath, bat)
        if debug:
            cprint(f"start_the_miner(): Path to miner: {path_to_miner}", to_log=to_log, q=q)
        subprocess.Popen(path_to_miner)
        time.sleep(2)  # Wait a few secs for the hashrate to reach the limit you set
    except Exception as err:
        cprint(f'Error in initiating the miner: {err}', to_log=to_log, q=q)
        if to_log:
            logging.info(f'{get_current_time()}Error in initiating the miner')


def start_the_oc_bat_file(Verbose=True, to_log=True, debug=False, q=''):
    # https://stackoverflow.com/questions/10965949/can-subprocess-call-be-invoked-without-waiting-for-process-to-finish
    """A function to start the overclocking bat named 'nvidia_oc.bat'.
        Firstly, it searches the arguments.json for the path.
       If json does not contain the key 'path_oc_bat', it searches current working directory"""
    try:
        json_data = ''
        cmd_args = []
        dirpath = ''
        path = sys.argv[0].split('\\')
        path = '\\'.join(path[:-1])
        if file_exist(os.path.join(path, 'arguments.json'), debug=debug, to_log=to_log, q=q, sole_output=debug):
            with open(os.path.join(path, 'arguments.json'), 'r+', encoding='utf-8') as file:
                json_data = json.load(file)
                if 'path_oc_bat' in json_data.keys():
                    dirpath = json_data['path_oc_bat']
                    cmd_args.append(dirpath)
                    cmd_args.append('start ')
                    cmd_args.append('/wait ')
                    if debug:
                        cprint(f'Path_oc_bat found in arguments.json', to_log=to_log, q=q)
                else:
                    dirpath = os.path.abspath(path)
                    filename = "nvidia_oc.bat"
                    cmd_args.append(os.path.join(dirpath, filename))
                    cmd_args.append('start ')
                    cmd_args.append('/wait ')
        else:
            dirpath = os.path.abspath(path)
            filename = "nvidia_oc.bat"
            cmd_args.append(os.path.join(dirpath, filename))
            cmd_args.append('start ')
            cmd_args.append('/wait ')
        # Through bat file, overclock bat file is running smoothly in the background
        bat_process = subprocess.Popen(cmd_args)
        if Verbose:
            cprint(f">>>{Fore.LIGHTGREEN_EX}Bat file successfully "
                   f"initiated with admin rights{Style.RESET_ALL}", to_log=to_log, q=q)
    except Exception as err:
        cprint(f'Error in initiating the overclock bat file: {err}', to_log=to_log, q=q)


def suspend_resume_miner(operation='', name='miner.exe', to_log=True, debug=False, q=''):
    """If operation is "suspend", it suspends the miner and its child processes
       If operation is "resume", it resumes them
       If "pid", it returns a list with the pids of the miner and its child processes"""
    name = exe_name_of_miner(name)
    #  The list containing dictionaries with the name and the pid of the miner and its child processes
    process_list_of_miner = []  # Clear the list
    # Iterate over all running process
    if operation == 'suspend':
        if debug:
            cprint(f'suspend_resume_miner(): operation set to {operation}', to_log=to_log, q=q)
        for process in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if name.lower() == process.name().lower():
                    process_info = process.as_dict(attrs=['name', 'pid'])
                    process_list_of_miner.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"Error in finding the process due to {err}", to_log=to_log, q=q)
        for _process in process_list_of_miner:
            try:
                process_pid = _process['pid']
                children = psutil.Process(process_pid).children(recursive=True)
                for child in children:
                    process_info = child.as_dict(attrs=['name', 'pid'])
                    process_list_of_miner.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"Error in finding the process due to {err}", to_log=to_log, q=q)
        if debug:
            cprint(f'suspend_resume_miner(): List of the process: {process_list_of_miner}', to_log=to_log, q=q)
        for process in process_list_of_miner:
            try:
                process_to_suspend = psutil.Process(process['pid'])
                if process_to_suspend.status() == psutil.STATUS_RUNNING:
                    process_to_suspend.suspend()
                    if not debug:
                        cprint(f'Process {process_to_suspend.name()} is suspended', to_log=to_log, q=q)
                    if debug:
                        cprint(f'suspend_resume_miner(): {process_to_suspend} is suspended.', to_log=to_log, q=q)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"suspend_resume_miner(): Error in finding the process due to {err}", to_log=to_log, q=q)
    elif operation == 'resume':
        if debug:
            cprint(f'suspend_resume_miner(): operation set to {operation}', to_log=to_log, q=q)
        for process in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if name.lower() == process.name().lower():
                    process_info = process.as_dict(attrs=['name', 'pid'])
                    process_list_of_miner.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"suspend_resume_miner(): Error in finding the process due to {err}", to_log=to_log, q=q)
        for process in process_list_of_miner:
            try:
                children = psutil.Process(process['pid']).children(recursive=True)
                for child in children:
                    process_info = child.as_dict(attrs=['name', 'pid'])
                    process_list_of_miner.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"suspend_resume_miner(): Error in finding the process due to {err}", to_log=to_log, q=q)
        if debug:
            cprint(f'suspend_resume_miner(): List of the process: {process_list_of_miner}', to_log=to_log, q=q)
        for process in process_list_of_miner:
            try:
                process_to_suspend = psutil.Process(process['pid'])
                if process_to_suspend.status() == psutil.STATUS_STOPPED or psutil.STATUS_SLEEPING:
                    process_to_suspend.resume()
                    if not debug:
                        cprint(f'Process {process_to_suspend.name()} is resumed', to_log=to_log, q=q)
                    if debug:
                        cprint(f'suspend_resume_miner(): {process_to_suspend} is resumed.', to_log=to_log, q=q)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"suspend_resume_miner(): Error in finding the process due to {err}", to_log=to_log, q=q)
    #  Return a list of dictionaries with the miner's name and pid (+ its children)
    elif operation == 'pid':
        if debug:
            cprint(f'suspend_resume_miner(): operation set to {operation}', to_log=to_log, q=q)
        for process in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if name.lower() == process.name().lower():
                    process_info = process.as_dict(attrs=['name', 'pid'])
                    process_list_of_miner.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"suspend_resume_miner(): Error in finding the process due to {err}", to_log=to_log, q=q)
        for process in process_list_of_miner:
            try:
                children = psutil.Process(process['pid']).children(recursive=True)
                for child in children:
                    process_info = child.as_dict(attrs=['name', 'pid'])
                    process_list_of_miner.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as err:
                cprint(f"suspend_resume_miner(): Error in finding the process due to {err}", to_log=to_log, q=q)
        return process_list_of_miner


def check_write_update_json_arguments(debug, path_to_arguments_json, arguments: dict, to_log, q, json_data):
    """
    Checks if the file exists, load its content, update its dictionary with the arguments and then overwrite the json.
    If it does not exist, creates a new one.
    :param debug: Boolean
    :param path_to_arguments_json: The path to arguments.json
    :param arguments: A dictionary containing all arguments
    :param to_log: Boolean
    :param q: The Queue object
    :param json_data: The data from arguments.json (if the .json exists).
    :return: None
    """
    try:
        if file_exist('arguments.json', debug=str2bool(debug)):
            if debug:
                cprint(f'arguments.json exists', to_log=to_log, q=q)
            with open(path_to_arguments_json, 'r+', encoding='utf-8') as file:
                json_data = json.load(file)
                if len(json_data) == 0:  # To avoid empty string in the text file
                    json_data = arguments
                else:
                    json_data.update(arguments)
            with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
                json.dump(json_data, file, indent=4)
                if debug:
                    cprint(f'main(): Json data is written in {path_to_arguments_json}', to_log=to_log, q=q)
        # If it does not exist, just create a new one.
        else:
            with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
                json.dump(json_data, file, indent=4)
                if debug:
                    cprint(f'main(): Json data is written in {path_to_arguments_json}', to_log=to_log, q=q)
    except BaseException as err:
        cprint(f'Error in opening json file. {err}'
               f'\nPath_to_arguments_json: {path_to_arguments_json}')
        time.sleep(5)
