import json
import multiprocessing as mp
import os
import sys
import time
import colorama
import psutil
from colorama import Fore, Style
from helper_functions import str2bool, exe_name_of_miner, cprint, countdown_to_restart_whole_process, \
    restart_whole_process, suspend_resume_miner
from misc.logger_ import start_logging, check_filemode, check_path


def check_if_power_cable_is_plugged(color=True, logfile='logfile.txt', debug=False, sole_output=False, to_log=True,
                                    q=mp.Queue, path='', miner='miner.exe', stratumproxy='stratumproxy',
                                    mode='no_battery'):
    """
    Checks constantly (in while True loop) if the power cable is on.
    If mode = 'battery', it constantly checks in the cable is on.
    If mode = 'no_battery', it sleeps for 10 secs.
    If mode is set to something else, it sleeps for 30000 secs. (i.e. it's running on a desktop).
    :param color: Boolean: Whether the output in terminal contains color or not.
    :param logfile: The name of the logfile.
    :param debug: Boolean
    :param sole_output: Boolean
    :param to_log: Boolean: Whether it logs the outputs or not
    :param q: The Queue object
    :param path: The current path which the exe is running from
    :param miner: The miner's name
    :param stratumproxy: The stratum proxy name
    :param mode: The mode of the battery ("no_battery" or something else). If there is a cable on,
                 the argument does nothing.
    :return: None
    """
    sys.stderr = sys.stdout
    color = str2bool(color)
    debug = str2bool(debug)
    to_log = str2bool(to_log)
    q = q
    path = path
    miner = exe_name_of_miner(miner)
    stratumproxy = exe_name_of_miner(stratumproxy)
    colorama.init(convert=bool(color))
    # Calls the function to return and save the string to a variable and then it will be passed to logging
    path_to_file = check_path(logfile=logfile, debug=debug, sole_output=sole_output, to_log=to_log, q=q)
    # Calls the function to return and save the string to a variable and then it will be passed to logging
    log_mode = check_filemode(path=path_to_file, logfile=logfile, debug=debug, sole_output=sole_output, to_log=to_log,
                              q=q)
    start_logging(path_to_file, log_mode)
    internet_pid = ''
    json_data = ''
    main_loop_pid = ''
    with open(os.path.join(path, 'arguments.json'), 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        internet_pid = int(json_data['process_internet_pid'])
        main_loop_pid = int(json_data['process_main_loop_pid'])
    process_internet_psutil = psutil.Process(internet_pid)
    process_main_loop_psutil = psutil.Process(main_loop_pid)
    while True:
        processes_of_miner = []
        processes_of_stratumproxy = []
        try:
            # Predetermine that the system has a battery
            if psutil.sensors_battery():
                if psutil.sensors_battery().power_plugged:
                    cprint(f'Power cable is plugged', to_log=to_log, q=q)
                    # If pid doesn't exist, or it is reused by another process, restart the whole script.
                    if psutil.pid_exists(process_internet_psutil.pid) is False or psutil.Process(
                            process_internet_psutil.pid).name() != process_internet_psutil.name():
                        countdown_to_restart_whole_process(process_main_loop_psutil, to_log, q)
                    if process_internet_psutil.status() == psutil.STATUS_STOPPED:
                        try:
                            process_internet_psutil.resume()
                            if not debug:
                                cprint(f'{Fore.LIGHTGREEN_EX}{process_internet_psutil.name()} '
                                       f'{process_internet_psutil.pid} is initiated{Style.RESET_ALL}', to_log=to_log,
                                       q=q)
                            if debug:
                                cprint(f'check_if_power_cable_is_plugged(): {process_internet_psutil} is initiated',
                                       to_log=to_log, q=q)
                        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied, psutil.Error) as err:
                            cprint(f'Process {process_internet_psutil.name()} failed to resume due to {err}',
                                   to_log=to_log, q=q)
                            cprint(f"Error: {err} \t process_internet_psutil: {process_internet_psutil.status()}",
                                   to_log=to_log, q=q)
                    elif process_internet_psutil.status() == psutil.STATUS_DEAD:
                        if not debug:
                            cprint(f'Process {process_internet_psutil.name()} was terminated. Restarting the '
                                   f'whole process',
                                   to_log=to_log, q=q)
                        if debug:
                            cprint(f'Process {process_internet_psutil} was terminated. \nRestarting the '
                                   f'whole process',
                                   to_log=to_log, q=q)
                        restart_whole_process()
                    #  Get the processes of the miner and resume them, if the processes are stopped.
                    process_list_of_miner = suspend_resume_miner(operation='pid', name=miner, to_log=to_log, q=q,
                                                                 debug=debug)
                    process_list_of_stratumproxy = suspend_resume_miner(operation='pid', name=stratumproxy,
                                                                        to_log=to_log, q=q, debug=debug)
                    processes_of_miner = []  # Clear the list from previous processes
                    for process in process_list_of_miner:
                        miner_process = psutil.Process(process['pid'])
                        processes_of_miner.append(miner_process)
                    if len(processes_of_miner) != 0:
                        if debug:
                            cprint(f'checking_internet_connection(): processes_of_miner {processes_of_miner}',
                                   to_log=to_log, q=q)
                        for process in processes_of_miner:
                            if process.status() == psutil.STATUS_STOPPED:
                                try:
                                    process.resume()
                                    if not debug:
                                        cprint(
                                            f'{Fore.LIGHTGREEN_EX}Process {process.name()} is resumed.{Style.RESET_ALL}',
                                            to_log=to_log, q=q)
                                    if debug:
                                        cprint(f'checking_internet_connection(): Process {process} is resumed.',
                                               to_log=to_log, q=q)
                                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                    cprint(f'Process {process.name()} failed to resume due to {err}',
                                           to_log=to_log, q=q)  # The miner will be spawned through main_loop()
                    processes_of_stratumproxy = []  # Clear the list from previous processes
                    for process in process_list_of_stratumproxy:
                        miner_process = psutil.Process(process['pid'])
                        processes_of_stratumproxy.append(miner_process)
                    if len(processes_of_stratumproxy) != 0:
                        if debug:
                            cprint(f'checking_internet_connection(): processes_of_miner {processes_of_stratumproxy}',
                                   to_log=to_log, q=q)
                        for process in processes_of_stratumproxy:
                            if process.status() == psutil.STATUS_STOPPED:
                                try:
                                    process.resume()
                                    if not debug:
                                        cprint(
                                            f'{Fore.LIGHTGREEN_EX}Process {process.name()} is resumed.{Style.RESET_ALL}',
                                            to_log=to_log, q=q)
                                    if debug:
                                        cprint(f'checking_internet_connection(): Process {process} is resumed.',
                                               to_log=to_log, q=q)
                                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                    cprint(f'Process {process.name()} failed to resume due to {err}',
                                           to_log=to_log, q=q)  # The miner will be spawned through main_loop()

                    time.sleep(2.5)
                    continue
                else:
                    cprint(f"Power cable is NOT plugged.", to_log=to_log, q=q)
                    #  Suspend the processes
                    if psutil.pid_exists(process_internet_psutil.pid) is False or psutil.Process(
                            process_internet_psutil.pid).name() != process_internet_psutil.name():
                        countdown_to_restart_whole_process(process_main_loop_psutil, to_log, q)
                    if process_internet_psutil.status() == psutil.STATUS_RUNNING:
                        process_internet_psutil.suspend()
                        if not debug:
                            cprint(f'{Fore.LIGHTRED_EX}{process_internet_psutil.name()} is suspended.'
                                   f'{Style.RESET_ALL}', to_log=to_log, q=q)
                        if debug:
                            cprint(f'check_if_power_cable_is_plugged(): {process_internet_psutil} is suspended.',
                                   to_log=to_log, q=q)
                    if process_main_loop_psutil.status() == psutil.STATUS_RUNNING:
                        process_main_loop_psutil.suspend()
                        if not debug:
                            cprint(f'{Fore.LIGHTRED_EX}{process_main_loop_psutil.name()} is suspended.'
                                   f'{Style.RESET_ALL}', to_log=to_log, q=q)
                        if debug:
                            cprint(f'{process_main_loop_psutil} is suspended', to_log=to_log, q=q)
                    #  Get the processes of the miner and suspend them, if the processes are running.
                    process_list_of_miner = suspend_resume_miner(operation='pid', name=miner, to_log=to_log, q=q,
                                                                 debug=debug)
                    process_list_of_stratumproxy = suspend_resume_miner(operation='pid', name=stratumproxy,
                                                                        to_log=to_log, q=q, debug=debug)
                    processes_of_miner = []  # Clear the list from previous processes
                    for process in process_list_of_miner:
                        miner_process = psutil.Process(process['pid'])
                        processes_of_miner.append(miner_process)
                    if len(processes_of_miner) != 0:
                        if debug:
                            cprint(f'checking_internet_connection(): processes_of_miner {processes_of_miner}',
                                   to_log=to_log, q=q)
                        for process in processes_of_miner:
                            if process.status() == psutil.STATUS_RUNNING:
                                try:
                                    process.suspend()
                                    if not debug:
                                        cprint(
                                            f'{Fore.LIGHTGREEN_EX}Process {process.name()} is suspended.{Style.RESET_ALL}',
                                            to_log=to_log, q=q)
                                    if debug:
                                        cprint(f'checking_internet_connection(): Process {process} is suspended.',
                                               to_log=to_log, q=q)
                                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                    cprint(f'Process {process.name()} failed to be suspended due to {err}',
                                           to_log=to_log, q=q)
                    processes_of_stratumproxy = []  # Clear the list from previous processes
                    for process in process_list_of_stratumproxy:
                        miner_process = psutil.Process(process['pid'])
                        processes_of_stratumproxy.append(miner_process)
                    if len(processes_of_stratumproxy) != 0:
                        if debug:
                            cprint(f'checking_internet_connection(): processes_of_miner {processes_of_stratumproxy}',
                                   to_log=to_log, q=q)
                        for process in processes_of_stratumproxy:
                            if process.status() == psutil.STATUS_RUNNING:
                                try:
                                    process.suspend()
                                    if not debug:
                                        cprint(
                                            f'{Fore.LIGHTGREEN_EX}Process {process.name()} is suspended.{Style.RESET_ALL}',
                                            to_log=to_log, q=q)
                                    if debug:
                                        cprint(f'checking_internet_connection(): Process {process} is suspended.',
                                               to_log=to_log, q=q)
                                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                    cprint(f'Process {process.name()} failed to be suspended due to {err}',
                                           to_log=to_log, q=q)  # The miner will be spawned through main_loop()

                    time.sleep(3)
            #  If the system has not a battery (i.e. it's a desktop) or it can not be determined (see psutil docs)
            elif psutil.sensors_battery() is None or False:
                cprint("No battery detected", to_log=to_log, q=q)
                if debug:
                    cprint(f'psutil.sensors_battery(): {psutil.sensors_battery()}', to_log=to_log, q=q)
                if psutil.pid_exists(process_internet_psutil.pid) is False or psutil.Process(
                        process_internet_psutil.pid).name() != process_internet_psutil.name():
                    countdown_to_restart_whole_process(process_main_loop_psutil, to_log, q)
                if mode == 'no_battery':  # A laptop without battery
                    time.sleep(10)
                else:  # Desktop
                    time.sleep(30000)  # Restart every Χ seconds
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied, psutil.Error) as err:
            cprint(f'Error in checking cable: {err}', to_log=to_log, q=q)
            if debug:
                cprint(f"process_internet_psutil: {process_internet_psutil}", to_log=to_log, q=q)
                cprint(f"process_main_loop_psutil: {process_main_loop_psutil}", to_log=to_log, q=q)
            time.sleep(2)