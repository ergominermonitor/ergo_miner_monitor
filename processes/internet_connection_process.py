import json
import multiprocessing as mp
import os
import random
import socket
import sys
import time
import colorama
import psutil
from colorama import Fore, Style
from helper_functions import str2bool, exe_name_of_miner, cprint, countdown_to_restart_whole_process, \
    suspend_resume_miner, restart_whole_process
from logger_ import check_path, check_filemode, start_logging


def checking_internet_connection(color=True, logfile='logfile.txt', debug=False, sole_output=False, to_log=True,
                                 q=mp.Queue, path='', miner='miner.exe', stratumproxy='stratumproxy.exe'):
    """Constantly checks if there is an internet connection.
    https://stackoverflow.com/questions/20913411/test-if-an-internet-connection-is-present-in-python"""
    sys.stderr = sys.stdout
    color = str2bool(color)
    debug = str2bool(debug)
    to_log = str2bool(to_log)
    q = q
    path = path
    miner = exe_name_of_miner(miner)
    stratumproxy = exe_name_of_miner(stratumproxy)
    #  This function is called through multiprocessing.Process and
    #  the Colorama needs to be initiated in this separated process
    colorama.init(convert=bool(color))
    # Call the function to save the returned string to a variable and then it will be passed to logging
    path_to_file = check_path(logfile=logfile, debug=debug, sole_output=sole_output, to_log=to_log, q=q)
    # Call the function to save the returned string to a variable and then it will be passed to logging
    log_mode = check_filemode(path=path_to_file, logfile=logfile, debug=debug, sole_output=sole_output, to_log=to_log,
                              q=q)
    start_logging(path_to_file, log_mode)
    dns = ["1.1.1.1", "1.0.0.1", "208.67.222.222", "208.67.220.220", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112",
           "76.76.19.19", "76.223.122.150", "94.140.14.14", "94.140.15.15"]
    dns_copy = ["1.1.1.1", "1.0.0.1", "208.67.222.222", "208.67.220.220", "8.8.8.8", "8.8.4.4", "9.9.9.9",
                "149.112.112.112", "76.76.19.19", "76.223.122.150", "94.140.14.14", "94.140.15.15"]
    #  Define the pid of the other multiprocessing Processes through the txt file
    cable_pid = ''
    main_loop_pid = ''
    processes_of_miner = []
    with open(os.path.join(path, 'arguments.json'), 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        cable_pid = int(json_data['process_cable_pid'])
        main_loop_pid = int(json_data['process_main_loop_pid'])
    process_cable_psutil = psutil.Process(cable_pid)
    process_main_loop_psutil = psutil.Process(main_loop_pid)
    socket.setdefaulttimeout(2)
    url = ''
    #  The while loop checking for internet connection by pinging the aforementioned dns
    while True:
        if len(dns_copy) == 0:
            for x in dns:
                dns_copy.append(x)
            if debug:
                cprint(f'Dns_copy is renewed: {dns_copy}', to_log=to_log, q=q)
                cprint(f'DNS: {dns}', to_log=to_log, q=q)
        try:
            # If pid doesn't exist, or it is reused by another process, restart the whole script.
            if psutil.pid_exists(process_cable_psutil.pid) is False or psutil.Process(
                    process_cable_psutil.pid).name() != process_cable_psutil.name():
                countdown_to_restart_whole_process(process_main_loop_psutil, to_log, q)
            # Connect to the host and tells us if the host is actually reachable
            url = random.choice(dns)
            cprint(f'Checking internet connection by creating a connection to "{url}".', to_log=to_log, q=q)
            sock = socket.create_connection((f'{url}', 80), timeout=2)  # tuple (address, port)
            if sock is not None:
                cprint(f'Closing socket to "{url}"', to_log=to_log, q=q)
                sock.close()
                #  If the processes are stopped, we resume them.
                try:
                    if process_cable_psutil.status() == psutil.STATUS_STOPPED:
                        process_cable_psutil.resume()
                        if debug:
                            cprint(f'{Fore.LIGHTGREEN_EX}{process_cable_psutil.name}(pid={process_cable_psutil.pid}) '
                                   f'is initiated{Style.RESET_ALL}',
                                   to_log=to_log, q=q)
                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                    cprint(f'Error in resuming {process_cable_psutil} due to {err}', to_log=to_log, q=q)
                    if psutil.pid_exists(process_cable_psutil.pid) is False or psutil.Process(
                            process_cable_psutil.pid).name() != process_cable_psutil.name():
                        cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log, q=q)
                        countdown_to_restart_whole_process(process_main_loop_psutil, to_log=to_log, q=q)
                try:
                    if process_main_loop_psutil.status() == psutil.STATUS_STOPPED:
                        process_main_loop_psutil.resume()
                        if debug:
                            cprint(f'{Fore.LIGHTGREEN_EX}{process_main_loop_psutil} is initiated{Style.RESET_ALL}',
                                   to_log=to_log, q=q)
                except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                    cprint(f'Error in resuming {process_main_loop_psutil} due to {err}', to_log=to_log, q=q)
                    if psutil.pid_exists(process_main_loop_psutil.pid) is False or psutil.Process(
                            process_main_loop_psutil.pid).name() != process_main_loop_psutil.name():
                        cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log, q=q)
                        time.sleep(2)
                        countdown_to_restart_whole_process(process_main_loop_psutil, to_log=to_log, q=q)
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
                                    cprint(f'{Fore.LIGHTGREEN_EX}Process {process.name()} is resumed.{Style.RESET_ALL}',
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
                                    cprint(f'{Fore.LIGHTGREEN_EX}Process {process.name()} is resumed.{Style.RESET_ALL}',
                                           to_log=to_log, q=q)
                                if debug:
                                    cprint(f'checking_internet_connection(): Process {process} is resumed.',
                                           to_log=to_log, q=q)
                            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                cprint(f'Process {process.name()} failed to resume due to {err}',
                                       to_log=to_log, q=q)  # The miner will be spawned through main_loop()

                time.sleep(2.5)
        except (socket.error, TimeoutError) as err:
            if not debug:
                cprint(f'Creating connection to "{url}" failed.', to_log=to_log, q=q)
            if debug:
                cprint(f'checking_internet_connection(): Creating connection to "{url}" failed due to {err}.',
                       to_log=to_log, q=q)
            # Try 2nd time
            while True:
                # If pid doesn't exist, or it is reused by another process, restart the whole script.
                if psutil.pid_exists(process_cable_psutil.pid) is False or psutil.Process(
                        process_cable_psutil.pid).name() != process_cable_psutil.name():
                    cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log, q=q)
                    process_main_loop_psutil.suspend()  # Suspend main_loop, so as not to kill the new process
                    time.sleep(5)
                    restart_whole_process()
                if len(dns_copy) == 0:  # Re-initiate the while loop
                    if debug:
                        cprint(f'checking_internet_connection(): dns_copy: {dns_copy}. Breaking the loop',
                               to_log=to_log, q=q)
                    break
                for x in dns_copy:
                    # If pid doesn't exist, or it is reused by another process, restart the whole script.
                    if psutil.pid_exists(process_cable_psutil.pid) is False or psutil.Process(
                            process_cable_psutil.pid).name() != process_cable_psutil.name():
                        cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log, q=q)
                        process_main_loop_psutil.suspend()  # Suspend main_loop, so as not to kill the new process
                        time.sleep(5)
                        restart_whole_process()
                    if debug:
                        cprint(f'checking_internet_connection(): dns_copy: {dns_copy}', to_log=to_log, q=q)
                    try:
                        dns_server = random.choice(dns_copy)  # Picks a random dns
                        cprint(f'Checking "{dns_server}" ', to_log=to_log, q=q)
                        sock2 = socket.create_connection((f"{dns_server}", 53), timeout=2)
                        if sock2 is not None:
                            cprint(f'Closing socket to "{dns_server}"', to_log=to_log, q=q)
                            sock2.close()
                            #  If the processes are stopped, we resume them.
                            try:
                                if process_cable_psutil.status() == psutil.STATUS_STOPPED:
                                    process_cable_psutil.resume()
                                    cprint(f'{Fore.LIGHTGREEN_EX}{process_cable_psutil} is initiated{Style.RESET_ALL}',
                                           to_log=to_log, q=q)
                            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                cprint(f'Error in resuming {process_cable_psutil} due to {err}', to_log=to_log, q=q)
                                if psutil.pid_exists(process_main_loop_psutil.pid) is False or psutil.Process(
                                        process_main_loop_psutil.pid).name() != process_main_loop_psutil.name():
                                    cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log,
                                           q=q)
                                    time.sleep(2)
                                    countdown_to_restart_whole_process(process_main_loop_psutil, to_log=to_log, q=q)
                            try:
                                if process_main_loop_psutil.status() == psutil.STATUS_STOPPED:
                                    process_main_loop_psutil.resume()
                                    cprint(
                                        f'{Fore.LIGHTGREEN_EX}{process_main_loop_psutil} is initiated{Style.RESET_ALL}',
                                        to_log=to_log, q=q)
                            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                cprint(f'Error in resuming {process_main_loop_psutil} due to {err}', to_log=to_log, q=q)
                                if psutil.pid_exists(process_main_loop_psutil.pid) is False or psutil.Process(
                                        process_main_loop_psutil.pid).name() != process_main_loop_psutil.name():
                                    cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log,
                                           q=q)
                                    time.sleep(2)
                                    countdown_to_restart_whole_process(process_main_loop_psutil, to_log=to_log, q=q)
                            #  Get the processes of the miner and resume them, if the processes are stopped.
                            process_list_of_miner = suspend_resume_miner(operation='pid', name=miner,
                                                                         to_log=to_log, q=q, debug=debug)
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
                                    cprint(f'checking_internet_connection(): '
                                           f'processes_of_miner {processes_of_stratumproxy}',
                                           to_log=to_log, q=q)
                                for process in processes_of_stratumproxy:
                                    if process.status() == psutil.STATUS_STOPPED:
                                        try:
                                            process.resume()
                                            if not debug:
                                                cprint(f'{Fore.LIGHTGREEN_EX}Process {process.name()} is resumed.'
                                                       f'{Style.RESET_ALL}',
                                                       to_log=to_log, q=q)
                                            if debug:
                                                cprint(f'checking_internet_connection(): Process {process} is resumed.',
                                                       to_log=to_log, q=q)
                                        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                            cprint(f'Process {process.name()} failed to resume due to {err}',
                                                   to_log=to_log, q=q)  # The miner will be spawned through main_loop()

                            time.sleep(2.5)
                    except (socket.error, TimeoutError) as err:
                        #  sock2 is None:
                        dns_copy.remove(f'{x}')
                        if debug:
                            cprint(f'checking_internet_connection(): {err}')
                            cprint(f'checking_internet_connection(): Current dns list: {dns_copy}', to_log=to_log, q=q)
                        cprint(f'{Fore.RED}No internet connection{Style.RESET_ALL}', to_log=to_log, q=q)
                        #  If the processes are running, we suspend them.
                        try:
                            if process_cable_psutil.status() == psutil.STATUS_RUNNING:
                                process_cable_psutil.suspend()
                                cprint(f'{Fore.LIGHTRED_EX}{process_cable_psutil} is suspended{Style.RESET_ALL}',
                                       to_log=to_log, q=q)
                        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                            cprint(f'Error in suspending {process_cable_psutil} due to {err}', to_log=to_log, q=q)
                        try:
                            if process_main_loop_psutil.status() == psutil.STATUS_RUNNING:
                                process_main_loop_psutil.suspend()
                                cprint(f'{Fore.LIGHTRED_EX}{process_main_loop_psutil} is suspended{Style.RESET_ALL}',
                                       to_log=to_log, q=q)
                        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                            cprint(f'Error in suspending {process_main_loop_psutil} due to {err}', to_log=to_log, q=q)
                        #  Get the processes of the miner and if the processes are running, we suspend them.
                        process_list_of_miner = suspend_resume_miner(operation='pid', name=miner,
                                                                     to_log=to_log, q=q, debug=debug)
                        process_list_of_stratumproxy = suspend_resume_miner(operation='pid', name=stratumproxy,
                                                                            to_log=to_log, q=q, debug=debug)
                        processes_of_miner = []
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
                                            cprint(f'{Fore.LIGHTRED_EX}Process {process.name()} is suspended.'
                                                   f'{Style.RESET_ALL}',
                                                   to_log=to_log, q=q)
                                        if debug:
                                            cprint(
                                                f'checking_internet_connection(): Process {process} is suspended.',
                                                to_log=to_log, q=q)
                                    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                        cprint(f'Process {process.name()} failed to suspend due to {err}',
                                               to_log=to_log, q=q)
                        processes_of_stratumproxy = []
                        for process in process_list_of_stratumproxy:
                            miner_process = psutil.Process(process['pid'])
                            processes_of_stratumproxy.append(miner_process)
                        if len(processes_of_stratumproxy) != 0:
                            if debug:
                                cprint(f'checking_internet_connection(): '
                                       f'processes_of_miner {processes_of_stratumproxy}',
                                       to_log=to_log, q=q)
                            for process in processes_of_stratumproxy:
                                if process.status() == psutil.STATUS_RUNNING:
                                    try:
                                        process.suspend()
                                        if not debug:
                                            cprint(f'{Fore.LIGHTRED_EX}Process {process.name()} is suspended.'
                                                   f'{Style.RESET_ALL}',
                                                   to_log=to_log, q=q)
                                        if debug:
                                            cprint(
                                                f'checking_internet_connection(): Process {process} is suspended.',
                                                to_log=to_log, q=q)
                                    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied) as err:
                                        cprint(f'Process {process.name()} failed to suspend due to {err}',
                                               to_log=to_log, q=q)
                        time.sleep(2.5)
