###############################################################
# miner watchdog 15/10/22 => bug fixes, refactoring #
################################################################
import random, socket, os, colorama, requests, time, psutil, sys, decimal
import itertools
import json, pathlib, queue
import multiprocessing as mp
from colorama import Style, Fore, Back
from datetime import datetime
import argparse
import nvidia_gpu
from helper_functions import is_admin, str2bool, exe_name_of_miner, bat_name_of_miner, get_current_time, \
    cprint, without_colorama, file_exist, prompt_to_acquire_admin_rights_and_exit, get_name_of_current_exe, \
    restart_whole_process, headers, checkIfProcessRunning, killiftheprocess, countdown_to_restart_whole_process, \
    start_the_miner, start_the_oc_bat_file, suspend_resume_miner, findAllProcessesRunning, trace_error, \
    check_write_update_json_arguments
from logger_ import check_path, check_filemode, start_logging
from pools.call_pool import call_pool, call_flypool_api
from miner.miner_api import get_infos

colorama.init(convert=False)  # True to pass the coloured text to the windows cmd. False for python console.

Verbose = None
Verbose_dev = None
#  Sample from json
json_example = '''"{  
        "gpus":1 ,  "devices" : 
        [  
        {  "devname" : "GeForce RTX 3060 Laptop GPU" ,  
        "pciid" : "00000000:01:00.0" ,  
        "UUID" : "GPU-5c28" ,  
        "hashrate" : 62.0918 ,  
        "fan" : 0 ,  
        "power" : 52 ,  
        "temperature" : 63 } ] 
        , "total": 62.0918 , "uptime": "0h"  
        }"'''

process_list = []


def kill_other_instances(name="", to_log=True, Verbose=True, main_parent_pid='',
                         debug=False, q=''):
    """If there are any other instances, it tries to kill them (Child & Parent processes)"""
    process_list = []
    if name == "":
        name = get_name_of_current_exe()
    debug = str2bool(debug)  # To be sure that debug is a bool and not a string
    main_parent_pid = int(main_parent_pid) if len(str(main_parent_pid)) != 0 else None
    if Verbose:
        cprint(f'{Fore.LIGHTGREEN_EX}'
               f'Checking if there is another instance running..'
               f'{Style.RESET_ALL}', to_log=to_log, q=q)
    try:  # [{'name': 'miner.exe', 'pid': 4556}, {'name': 'miner_api.exe', 'pid': 6740}]
        own_child_dict = {name: []}
        own_child_dict[name].append(main_parent_pid)  # Include main parent pid in the list
        try:
            # In exe the parent process has the same name
            parent_process = psutil.Process(os.getppid())
            if debug:
                cprint(f'parent_process: {parent_process}', to_log=to_log, q=q)
            # own_child_dict[parent_process.name()] = parent_process.pid
            if parent_process.name() in own_child_dict.keys():
                own_child_dict[name].append(parent_process.pid)
            else:
                own_child_dict[parent_process.name()] = parent_process.pid
            if debug:
                cprint(f'Dictionary of processes with parent: {own_child_dict}', to_log=to_log, q=q)
        except Exception as err:
            if not debug:
                cprint(f"Error in parent process", to_log=to_log, q=q)
            elif debug:
                cprint(f"Error in parent process: {err}", to_log=to_log, q=q)
        try:
            #  Parent pid
            if os.getppid():
                children = psutil.Process(os.getppid()).children(recursive=True)
                if debug:
                    cprint(f"Children process of current process:", to_log=to_log, q=q)
                for child in children:
                    if child.name() == name:
                        own_child_dict[name].append(child.pid)
                    else:
                        own_child_dict[child.name()] = child.pid
                    if debug:
                        cprint(f"{Fore.LIGHTGREEN_EX}{child.name()} : {child.pid}{Style.RESET_ALL}", to_log=to_log, q=q)
            else:
                #  Own pid
                own_child_dict[name].append(os.getpid())
                children = psutil.Process(os.getpid()).children(recursive=True)
                if debug:
                    cprint(f"Children process of current process:", to_log=to_log, q=q)
                for child in children:
                    if child.name() == name:
                        own_child_dict[name].append(child.pid)
                    else:
                        own_child_dict[child.name()] = child.pid

                    if debug:
                        cprint(f"{Fore.LIGHTGREEN_EX}{child.name()} : {child.pid}{Style.RESET_ALL}"
                               , to_log=to_log, q=q)
        except Exception as err:
            if not debug:
                cprint(f"{Fore.RED}Error in own children{Style.RESET_ALL}", to_log=to_log, q=q)
            elif debug:
                cprint(f"{Fore.RED}Error in own children: {err}{Style.RESET_ALL}", to_log=to_log, q=q)
        if Verbose:
            for key, value in own_child_dict.items():
                if debug:
                    cprint(f"{key} : {value}", to_log=to_log, q=q)
        if debug:
            cprint(f'Dictionary of processes: {own_child_dict}', to_log=to_log, q=q)
        process_list = findAllProcessesRunning(name, to_print=False, to_log=to_log,
                                               q=q)  # The process list is empty? Modify the function to return the process list
        for procc in process_list:
            try:
                process_list = findAllProcessesRunning(name, to_print=False, to_log=to_log, q=q)
                if procc['name'] == name:
                    if procc['pid'] not in own_child_dict.values():
                        if procc['pid'] not in own_child_dict[name]:
                            if procc in process_list:
                                if Verbose:
                                    if debug:
                                        cprint(f'Checking: \t{procc}', to_log=to_log, q=q)
                                # Constantly checking if this dictionary exists, because it could be killed in
                                # previous round of the loop
                                try:
                                    process_list = findAllProcessesRunning(name, to_print=False, to_log=to_log, q=q)
                                    if procc in process_list:
                                        children = psutil.Process(procc['pid']).children(recursive=True)
                                        for child in children:
                                            os.kill(child.pid, 9)
                                            cprint(f"\t{Fore.LIGHTGREEN_EX}"
                                                   f"Child process {child.name()} : {child.pid} killed"
                                                   f" successfully{Style.RESET_ALL}", to_log=to_log, q=q)
                                except Exception as err:
                                    if not debug:
                                        cprint(f"Error in killing children processes of {procc['pid']}", to_log=to_log,
                                               q=q)
                                    elif debug:
                                        cprint(f"Error in killing children processes of {procc['pid']} due to: {err}",
                                               to_log=to_log, q=q)
                                try:
                                    process_list = findAllProcessesRunning(name, to_print=False, to_log=to_log, q=q)
                                    if procc in process_list:
                                        parent_process = psutil.Process(procc['pid'])
                                        os.kill(parent_process.pid, 9)
                                        cprint(f"{Fore.LIGHTGREEN_EX}Parent process {parent_process.pid} killed"
                                               f" successfully{Style.RESET_ALL}", to_log=to_log, q=q)
                                except Exception as err:
                                    if not debug:
                                        cprint(f"Error in killing parent process of {procc['pid']}", to_log=to_log, q=q)
                                    elif debug:
                                        cprint(f"Error in killing parent process of {procc['pid']} due to {err}",
                                               to_log=to_log, q=q)
                                process_list = findAllProcessesRunning(name, to_print=False, to_log=to_log, q=q)
                                if procc in process_list:
                                    cprint(f"Current dictionary: {procc}", to_log=to_log, q=q)
                                    key = procc['name']
                                    time.sleep(15)
                                    os.kill(procc['pid'], 9)
                                    cprint(f"{Fore.LIGHTGREEN_EX}{key} : {procc['pid']} killed "
                                           f"successfully{Style.RESET_ALL}", to_log=to_log, q=q)
                            else:
                                if Verbose:
                                    cprint(f"Dictionary not found. "
                                           f"Probably it is already killed", to_log=to_log, q=q)
                    else:
                        pass
                else:
                    pass
            except Exception as err:
                if not debug:
                    cprint("Error in killing processes", to_log=to_log, q=q)
                    raise err
                elif debug:
                    cprint(f"Error in killing processes: {err}", to_log=to_log, q=q)
        if Verbose:
            cprint(f"{Fore.LIGHTGREEN_EX}"
                   f"Stop trying to kill the other instances{Style.RESET_ALL}"
                   f"\n", to_log=to_log, q=q)
    except Exception as err:  # (psutil.NoSuchProcess, psutil.AccessDenied) as err:
        cprint(f"Killing_other_instances Function error due to {err}", to_log=to_log, q=q)


def check_if_power_cable_is_plugged(color=True, logfile='logfile.txt', debug=False, sole_output=False, to_log=True,
                                    q=mp.Queue, path='', miner='miner.exe', stratumproxy='stratumproxy',
                                    mode='no_battery'):
    """Checks if the power cable is on"""
    sys.stderr = sys.stdout
    color = str2bool(color)
    debug = str2bool(debug)
    to_log = str2bool(to_log)
    q = q
    path = path
    miner = exe_name_of_miner(miner)
    stratumproxy = exe_name_of_miner(stratumproxy)
    colorama.init(convert=bool(color))
    # Call the function to return and save the string to a variable and then it will be passed to logging
    path_to_file = check_path(logfile=logfile, debug=debug, sole_output=sole_output, to_log=to_log, q=q)
    # Call the function to return and save the string to a variable and then it will be passed to logging
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


def main_loop(retries=5, to_log=True, URL='', retry_sec=5, miner='miner', stratumproxy='stratumproxy', Verbose=True,
              Verbose_dev=True,
              targettotalhashrate=71, color=True, logfile='logfile.txt', wallet='', main_parent_pid='', debug=False,
              bat_file='', flypool_to_be_called=False, q='', nvidia=True, pool='woolypooly', overclock_settings="",
              overclock='external', path=""):
    start = time.time()
    sys.stderr = sys.stdout
    retries = int(retries)
    to_log = str2bool(to_log)
    url = URL
    retry_sec = int(retry_sec)
    miner = miner
    Verbose = Verbose
    Verbose_dev = Verbose_dev
    targettotalhashrate = int(targettotalhashrate)
    main_parent_pid = main_parent_pid
    debug = str2bool(debug)
    bat_file = bat_file
    flypool_to_be_called = str2bool(flypool_to_be_called)
    q = q
    with open(os.path.join(path, 'arguments.json'), 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        process_cable_pid = int(json_data['process_cable_pid'])
        process_internet_pid = int(json_data['process_internet_pid'])
        process_main_loop_pid = int(json_data['process_main_loop_pid'])
    process_cable_psutil = psutil.Process(process_cable_pid)
    process_internet_psutil = psutil.Process(process_internet_pid)
    process_main_loop_psutil = psutil.Process(process_main_loop_pid)
    if overclock_settings != "" or not None:
        overclock_settings = overclock_settings.replace(")", "").replace("(", "").split(",")
        memory_offset = overclock_settings[0::2]
        memory_offset = [a.strip() for a in memory_offset]
        core_offset = overclock_settings[1::2]
        core_offset = [b.strip() for b in core_offset]
        if debug:
            cprint(f"To achieve: Core offset:{core_offset}, memory offset: {memory_offset}", to_log=to_log, q=q)
    colorama.init(convert=str2bool(color))
    # Call the function to return and save the string to a variable, and then it will be passed to logging
    path_to_file = check_path(logfile=logfile, debug=debug, to_log=to_log, q=q, sole_output=False)
    log_mode = check_filemode(path=path_to_file, logfile=logfile, debug=debug, to_log=to_log, q=q, sole_output=False)
    start_logging(path_to_file, log_mode)
    if nvidia:
        gpus = list(nvidia_gpu.get_all_gpus().values())  # A list with all the bus slots
    count = 0  # Counts how many times the hashrate was below the threshold that was given.
    url_reconnections = 0  # Counts the reconnections attempts
    if debug:
        path_main_loop = sys.argv[0].split('\\')[0]
        cprint(f"Main_loop is running from: {path_main_loop}", to_log=to_log, q=q)
    while True:
        kill_other_instances(name=get_name_of_current_exe(), Verbose=Verbose, main_parent_pid=main_parent_pid,
                             to_log=to_log, debug=debug, q=q)
        miner_status = checkIfProcessRunning(exe_name_of_miner(miner),
                                             to_print=True, Verbose=Verbose, to_log=to_log, q=q)
        stratumproxy_status = checkIfProcessRunning(exe_name_of_miner(stratumproxy),
                                                    to_print=True, Verbose=Verbose, to_log=to_log, q=q)
        #  Checkpoint
        if not miner_status or not stratumproxy_status:
            if not miner_status:
                killiftheprocess(processName=exe_name_of_miner(stratumproxy), to_log=to_log, q=q)
            elif not stratumproxy_status:
                killiftheprocess(processName=exe_name_of_miner(miner), to_log=to_log, q=q)
            cprint(f'{Fore.LIGHTRED_EX}Miner or stratumproxy was not found.{Style.RESET_ALL}', to_log=to_log, q=q)
            if nvidia:
                oc_offset = nvidia_gpu.get_core_memory_offset(0)
                if oc_offset[0] < 0 or not oc_offset[1] > 0:
                    if debug:
                        cprint(f'GPU core offset: {oc_offset[0]} and memory offset: {oc_offset[1]}', to_log=to_log,
                               q=q)
                    if overclock == 'external':
                        start_the_oc_bat_file(Verbose=Verbose, to_log=to_log, debug=debug, q=q)
                    else:
                        '''number = 0
                        for (a, b) in (core_offset, memory_offset):
                            nvidia_gpu.gpu_overclock(number, core_offset, memory_offset)
                            cprint("Overclocked<<<<")'''
                        # TODO: call gpu_overclock with the overclock settings for all available gpus
                        pass
            start_the_miner(to_log=to_log, debug=debug, bat_file=bat_file, q=q)
            cprint(f'{Fore.LIGHTGREEN_EX}Miner\'s bat file was started.{Style.RESET_ALL}', to_log=to_log, q=q)
            time.sleep(3)
        # Check if process_cable_psutil or process_internet_pid are killed (not stopped)
        if psutil.pid_exists(process_cable_psutil.pid) is False or psutil.Process(
                process_cable_psutil.pid).name() != process_cable_psutil.name():
            cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log,
                   q=q)
            countdown_to_restart_whole_process(process_main_loop_psutil=process_main_loop_psutil, to_log=to_log, q=q)
        if psutil.pid_exists(process_internet_psutil.pid) is False or psutil.Process(
                process_internet_psutil.pid).name() != process_internet_psutil.name():
            cprint(f"{Fore.LIGHTRED_EX}Restarting the process{Style.RESET_ALL}", to_log=to_log,
                   q=q)
            countdown_to_restart_whole_process(process_main_loop_psutil=process_main_loop_psutil, to_log=to_log, q=q)
        # If the script can not implement the overclocking, kill the miner and re-initiate the loop
        oc_offset = nvidia_gpu.get_core_memory_offset(0)
        if nvidia:
            if oc_offset[0] <= 200 or not oc_offset[1] > 0:
                if count > 3 * retries:
                    if debug:
                        cprint(f'GPU core offset: {oc_offset[0]} and memory offset: {oc_offset[1]}', to_log=to_log, q=q)
                    cprint(f"Retries threshold reached({count}). Miner will be restarted.", to_log=to_log, q=q)
                    killiftheprocess(exe_name_of_miner(miner))
                    killiftheprocess(exe_name_of_miner(stratumproxy))
                    start_the_miner(bat_file=bat_file, debug=debug, to_log=to_log)
                    time.sleep(3)  # Wait the DAG to be generated
                    if overclock == 'external':
                        start_the_oc_bat_file(Verbose=Verbose, to_log=to_log, debug=debug, q=q)
                    else:
                        try:
                            number = 0
                            for memory, core in itertools.product(memory_offset, core_offset):
                                nvidia_gpu.gpu_overclock(number, memory, core)
                                cprint(f"{Fore.GREEN}GPU bus slot: {number} "
                                       f"Overclocked >>>> [memory]:{memory} [core]: {core}<<<<{Style.RESET_ALL}")
                        except Exception as err:
                            raise err
        elif not nvidia:
            if count > 3 * retries:
                cprint(f"Retries threshold reached({count}). Miner will be restarted.", to_log=to_log, q=q)
                killiftheprocess(exe_name_of_miner(miner))
                killiftheprocess(exe_name_of_miner(stratumproxy))
                start_the_miner(bat_file=bat_file, debug=debug, to_log=to_log)
                time.sleep(30)  # Wait the DAG to be generated
                if overclock == 'external':
                    start_the_oc_bat_file(Verbose=Verbose, to_log=to_log, debug=debug, q=q)
                else:
                    # TODO: call gpu_overclock with the overclock settings
                    pass
        try:
            title_hashrate_watchdog = f"#{Fore.BLACK}{7 * ' '}{Fore.RED}Hashrate " \
                                      f"{miner} Watchdog{Fore.BLACK}{7 * ' '}{Style.RESET_ALL}#"
            # Time frame #
            # https://stackoverflow.com/questions/7370801/how-to-measure-elapsed-time-in-python
            time_now = datetime.now()
            dt = str(time_now.strftime("%d-%m-%Y %H:%M:%S")) + \
                 '.{:02d}'.format(round(time_now.microsecond, -4))[:4]
            dt = 'Date: ' + dt
            # Time elapsed
            end = time.time()
            str_elapsed = ""
            if ((end - start) / 60) < 60:
                if ((end - start) / 60) < 2:
                    str_elapsed = f"Time elapsed: {((end - start) / 60):.2f} minute"
                else:
                    str_elapsed = f"Time elapsed: {((end - start) / 60):.2f} minutes"
            elif ((end - start) / 60) >= 60:
                if ((end - start) / 60) / 60 < 2:
                    str_elapsed = f"Time elapsed: {((end - start) / 60) / 60:.2f} hour"
                else:
                    str_elapsed = f"Time elapsed: {((end - start) / 60) / 60:.2f} hours"
            if '.py' in sys.argv[0].split('\\')[0]:  # Different format for Pycharm
                text = f'\n{36 * " " + title_hashrate_watchdog}' \
                       f'\n{43 * " " + str_elapsed}' \
                       f'\n{41 * " " + dt}' \
                       '\n\n---------------------------------------------------------------------------------' \
                       '-----------------------------' \
                       f'\n{22 * " "}******************************************************************' \
                       f'\n{22 * " "}--- GPU --- Hashrate (MH/s) --- Power (W) --- Temperature (oC) ---'
            else:  # If it is running as an .exe
                text = f'\n{36 * " " + title_hashrate_watchdog}' \
                       f'\n{43 * " " + str_elapsed}' \
                       f'\n{41 * " " + dt}' \
                       '\n\n---------------------------------------------------------------------------------' \
                       '-----------------------------' \
                       f'\n{22 * " "}******************************************************************' \
                       f'\n{22 * " "}--- GPU --- Hashrate (MH/s) --- Power (W) --- Temperature (oC) ---'
            gpu_infos = get_infos(to_log=to_log, q=q)
            if gpu_infos is not None:
                url_reconnections = 0  # Resetting the count after the script connected successfully to miner's API
                for a_key, b_value in gpu_infos.items():
                    if b_value[3] < 100:  # If power < 100, to be centered under Power column
                        text_to_be_added = f'\n{22 * " "}    {a_key.replace("gpu", "")}       {b_value[2]}              ' \
                                           f'{b_value[3]}                {b_value[4]}'
                        text = text + text_to_be_added
                    elif b_value[3] >= 100:
                        text_to_be_added = f'\n{22 * " "}    {a_key.replace("gpu", "")}       {b_value[2]}             ' \
                                           f'{b_value[3]}                {b_value[4]}'
                        text = text + text_to_be_added
                total_hashrate = gpu_infos['gpu0'][-2]
                text = text + f"\n{22 * ' '}******************************************************************"
                text = text + f'\n{22 * " "}Total hashrate : {total_hashrate}'
                if pool == 'woolypooly':
                    data = call_pool(pool=pool, wallet=wallet, to_log=to_log, q=q,
                                     debug=debug)  # Returns floats if possible, else strings
                    hashrate_3h = str(data[0]) if len(str(data[0])) == 0 else str(data[0]) if "?" in str(data[0]) else \
                        data[0]
                    hashrate_24 = str(data[1]) if len(str(data[1])) == 0 else str(data[1]) if "?" in str(data[1]) else \
                        data[1]
                    payment = float(data[2])
                    text = text + f"\n{22 * ' '}Pool: Hashrate 3h -- Hashrate 24h -- Balance"
                    if '.py' in sys.argv[0].split('\\')[0]:
                        text = text + f"\n{22 * ' '}        {hashrate_3h}          {hashrate_24}          {payment:0.2f}"
                    else:
                        text = text + f"\n{22 * ' '}       {hashrate_3h}           {hashrate_24}          {payment:0.2f}"
                elif pool == "herominers":
                    data = call_pool(pool=pool, wallet=wallet, to_log=to_log, q=q, debug=debug)
                    try:
                        hashrate_24 = float(data[3].strip("MH/s").strip() if data[3].strip("MH/s").strip() != '' else 0)
                    except TypeError:  # Data returned None
                        hashrate_24 = ''
                    except Exception as err:
                        trace_error(to_log=to_log, q=q)
                    text = text + f"\n{22 * ' '}Pool: Hashrate 1h -- Hashrate 6h -- Hashrate 24h -- Balance"
                    if '.py' in sys.argv[0].split('\\')[0]:
                        text = text + f"\n{22 * ' '}{6 * ' '}{data[1]}{5 * ' '}{data[2]}{5 * ' '}{data[3]}{5 * ' '}{data[-1]}"
                        try:
                            text = text + f"\n{22 * ' '}{6 * ' '}{30 * ' '}({round(hashrate_24 / float(total_hashrate), 4) * 100:0.2f})%"
                        except (ZeroDivisionError, TypeError, ValueError):
                            text = text + f"\n{22 * ' '}{6 * ' '}{30 * ' '}"  # An extra empty line
                    else:
                        text = text + f"\n{22 * ' '}{6 * ' '}{data[1]}{5 * ' '}{data[2]}{5 * ' '}{data[3]}{5 * ' '}{data[-1]}"
                        try:
                            text = text + f"\n{22 * ' '}{6 * ' '}{30 * ' '}({round(hashrate_24 / float(total_hashrate), 4) * 100:0.2f}%)"
                        except (ZeroDivisionError, TypeError, ValueError):
                            text = text + f"\n{22 * ' '}{6 * ' '}{30 * ' '}"  # An extra empty line
                    # Stale and invalid shares ratio
                    try:
                        text = text + f"\n{22 * ' '}{6 * ' '}Stale shares (ratio) -- Invalid shares (ratio)"
                        text = text + f"\n{22 * ' '}{6 * ' '}{data[5]} ({round(float(data[5]) / float(data[4]), 4) * 100:0.2f}%){13 * ' '}{data[6]} ({round(float(data[6]) / float(data[4]), 4) * 100:0.2f}%)"
                    except (ZeroDivisionError, TypeError, ValueError):
                        trace_error(to_log=to_log, q=q)
                        # Erase "Stale shares ratio -- Invalid shares ratio"
                        text = text.replace(f"\n{22 * ' '}{6 * ' '}Stale shares ratio -- Invalid shares ratio", '')
                elif pool == 'flypool':
                    flypool_text = call_flypool_api(wallet=wallet, flypool_to_be_called=flypool_to_be_called,
                                                    to_log=to_log, debug=debug, q=q)
                    text = text + flypool_text
                text = text + f'\n-------------------------------------------------------------------------------' \
                              f'-------------------------------'
                cprint(f'{text}', to_log=to_log, q=q, time=False)
                #  Restart the counting if the hashrate is above the target
                if decimal.Decimal(total_hashrate) > targettotalhashrate:
                    count = 0
                # If hashrate is below the target, counting goes on
                elif decimal.Decimal(total_hashrate) <= targettotalhashrate:
                    count += 1
                    if count > retries:
                        if nvidia:
                            oc_offset = nvidia_gpu.get_core_memory_offset(0)
                            if oc_offset[0] < 200 or oc_offset[1] < 300:
                                # Initiating the bat file
                                cprint(f"{Fore.LIGHTGREEN_EX}Initiating overclocking"
                                       f"{Style.RESET_ALL}", to_log=to_log, q=q)
                                if overclock == 'external':
                                    start_the_oc_bat_file(Verbose=Verbose, to_log=to_log, debug=debug, q=q)
                                else:
                                    try:
                                        number = 0
                                        for memory, core in itertools.product(memory_offset, core_offset):
                                            nvidia_gpu.gpu_overclock(number, memory, core)
                                            cprint(f"{Fore.GREEN}GPU bus slot: {number} "
                                                   f"Overclocked memory:{memory} core: {core}<<<<{Style.RESET_ALL}",
                                                   to_log=to_log, q=q)
                                    except Exception as err:
                                        trace_error(to_log=to_log, q=q)
                                        raise err
                                    # TODO: call gpu_overclock with the overclock settings
                                    pass
                                start = time.time()  # Re-initiate starting time.
                                time.sleep(10)  # Takes some time so as the hashrate to be >35 in the miner
                cprint(f'Checking hashrate Retries : {count}', to_log=to_log, q=q)
                # checkIfProcessRunning(miner, to_print=True, Verbose=Verbose, to_log=to_log, q=q)
                time.sleep(5)  # TODO create a variable to control this time.sleep
            else:  # If gpu_infos returns None
                count += 1
                url_reconnections += 1
                cprint(f"{Fore.RED}{Back.LIGHTWHITE_EX}"
                       f"Warning{Style.RESET_ALL}: "
                       f"Error in miner\'s API request after {url_reconnections} retries."
                       f"\n{get_current_time()}\t\t\t\t\tRetrying in {retry_sec} seconds.", to_log=to_log, q=q)
                time.sleep(retry_sec)
                if url_reconnections > 5:
                    if url_reconnections < 10:
                        cprint('{}The provided url cannot be found after {} {} {}tries...\n'
                               '{}\t{}'.format({get_current_time()},
                                               Fore.RED, url_reconnections,
                                               Style.RESET_ALL, Fore.RED,
                                               Style.RESET_ALL),
                               to_log=to_log, q=q)
                        if not checkIfProcessRunning(exe_name_of_miner(miner), to_print=True, to_log=to_log, q=q) \
                                or not checkIfProcessRunning(exe_name_of_miner(stratumproxy),
                                                             to_print=True, to_log=to_log, q=q):
                            cprint(f"Initiating new miner through "
                                   f".bat file", to_log=to_log, q=q)
                            start_the_miner(bat_file=bat_file, debug=debug, to_log=to_log)
                            time.sleep(30)  # Wait  the DAG to be generated
                            if overclock == 'external':
                                start_the_oc_bat_file(Verbose=Verbose, to_log=to_log, debug=debug, q=q)
                            else:
                                # TODO: call gpu_overclock with the overclock settings
                                pass
                        # Initiate the bat file
                        else:
                            start_the_oc_bat_file(Verbose=Verbose, to_log=to_log, debug=debug, q=q)
                    else:
                        cprint('{}The provided url cannot be found after {} {} {}tries...\n'
                               '{}{}'.format({get_current_time()},
                                             Fore.RED, url_reconnections,
                                             Style.RESET_ALL, Fore.RED,
                                             Style.RESET_ALL))
        except Exception as err:
            trace_error(to_log=to_log, q=q)
            if not debug:
                cprint(f"{Fore.RED}Error in miner's Api (main loop).{Style.RESET_ALL}\t "
                       f"Reconnections attempts: {url_reconnections}"
                       f"\n{get_current_time()}{Fore.RED}Error: {err}{Style.RESET_ALL}",
                       to_log=to_log, q=q)
            if debug:
                cprint(f"Error in main_loop: Error: {err}")
            time.sleep(2)


def main(arguments):
    arguments = arguments
    path = pathlib.Path(arguments['path'])
    q = arguments['q']
    color = str2bool(arguments['color'])
    debug = str2bool(arguments['debug'])
    to_log = str2bool(arguments['to_log'])
    colorama.deinit()  # Stops colorama in order to be re-initiated
    colorama.init(convert=color)
    main_parent_pid = os.getppid()  # The main parent pid is set here in order to be passed in main_loop()
    cprint(f'{Fore.LIGHTGREEN_EX}Hello world{Style.RESET_ALL}', to_log=to_log, q=q)
    if debug:
        print_current_pid = f"Current PID: {os.getpid()}"
        cprint(f'{print_current_pid}', to_log=to_log, q=q)
        cprint(f"Current parent PID: {os.getppid()}", to_log=to_log, q=q)
    if Verbose:
        cprint(f"The miner's name is '{Fore.LIGHTGREEN_EX}{miner}{Style.RESET_ALL}'\n", to_log=to_log, q=q)
    text = ""
    for key, value in arguments.items():
        if key == "q":
            pass
        else:
            text = text + "\n" + str(key) + ": " + str(value)
    cprint(f"Arguments passed:{text}", to_log=to_log, q=q)
    full_path = os.path.join(path)
    path_to_arguments_json = os.path.join(full_path, 'arguments.json')
    if debug:
        cprint(f'main(): Full path:{full_path}', to_log=to_log, q=q)
        cprint(f'main(): Path to arguments json: {path_to_arguments_json}', to_log=to_log, q=q)
    #  Main
    process_main_loop = mp.Process(target=main_loop, name='Main_Loop', args=(f'{retries}', f'{to_log}', f'{url}',
                                                                             f'{retry_sec}', f'{miner}',
                                                                             f'{arguments["stratumproxy"]}',
                                                                             f'{Verbose}',
                                                                             f'{Verbose_dev}', f'{targettotalhashrate}',
                                                                             f'{color}', f'{logfile}', f'{wallet}',
                                                                             f'{main_parent_pid}', f'{debug}',
                                                                             f'{bat_file}', f'{flypool_to_be_called}',
                                                                             q, nvidia, f'{arguments["pool"]}',
                                                                             f'{arguments["overclock_settings"]}',
                                                                             f'{arguments["overclock"]}', path
                                                                             ))
    process_cable = mp.Process(target=check_if_power_cable_is_plugged, name='Cable_checking',
                               args=(f'{color}', f'{logfile}', f'{str2bool(debug)}', False, f'{str2bool(to_log)}',
                                     q, path, f'{arguments["miner"]}', f'{arguments["stratumproxy"]}',
                                     f'{arguments["mode"]}'
                                     ))
    process_internet = mp.Process(target=checking_internet_connection, name='Internet_checking',
                                  args=(f'{color}', f'{logfile}', f'{str2bool(debug)}', False, f'{str2bool(to_log)}',
                                        q, path, f'{arguments["miner"]}', f'{arguments["stratumproxy"]}'
                                        ))
    arguments['q'] = 'None'  # Delete the Queue object from the arguments dict.
    # The q [in the first lines of main()] still holds the Queue object, though. Use that if you need the Queue.
    json_data = {}

    process_main_loop.start()
    psutil.Process(process_main_loop.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    arguments['process_main_loop_pid'] = process_main_loop.pid
    # Check if arguments.json exists and loads it.
    check_write_update_json_arguments(debug=debug, path_to_arguments_json=path_to_arguments_json,
                                      arguments=arguments, to_log=to_log, q=q, json_data=json_data)
    '''if file_exist('arguments.json', debug=str2bool(debug)):
        with open(path_to_arguments_json, 'r+', encoding='utf-8') as file:
            json_data = json.load(file)
            json_data.update(arguments)
        with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
            json.dump(json_data, file, indent=4)
    else:
        with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
            json.dump(json_data, file, indent=4)'''
    process_cable.start()
    psutil.Process(process_cable.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    arguments['process_cable_pid'] = process_cable.pid
    # Check if arguments.json exists and loads it.
    # Debug False, so as not to print anything. It prints only the first time, after process_main_loop starts.
    check_write_update_json_arguments(debug=False, path_to_arguments_json=path_to_arguments_json,
                                      arguments=arguments, to_log=to_log, q=q, json_data=json_data)
    '''if file_exist('arguments.json', debug=str2bool(debug)):
        with open(path_to_arguments_json, 'r+', encoding='utf-8') as file:
            json_data = json.load(file)
            json_data.update(arguments)
        with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
            json.dump(json_data, file, indent=4)
    else:
        with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
            json.dump(json_data, file, indent=4)'''
    process_internet.start()
    psutil.Process(process_internet.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    arguments['process_internet_pid'] = process_internet.pid
    # Debug False, so as not to print anything. It prints only the first time, after process_main_loop starts.
    check_write_update_json_arguments(debug=False, path_to_arguments_json=path_to_arguments_json,
                                      arguments=arguments, to_log=to_log, q=q, json_data=json_data)
    '''if file_exist('arguments.json', debug=str2bool(debug)):
        with open(path_to_arguments_json, 'r+', encoding='utf-8') as file:
            json_data = json.load(file)
            json_data.update(arguments)
        with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
            json.dump(json_data, file, indent=4)
    else:
        with open(path_to_arguments_json, 'w+', encoding='utf-8') as file:
            json.dump(json_data, file, indent=4)'''
    if str2bool(debug):
        cprint(f'parent: {os.getppid()}', to_log=to_log, q=q)
        cprint(f'current: {os.getpid()}', to_log=to_log, q=q)
        cprint(f'process_cable: {process_cable.pid}', to_log=to_log, q=q)
        cprint(f'process_internet: {process_internet.pid}', to_log=to_log, q=q)
        cprint(f'process_main_loop: {process_main_loop.pid}', to_log=to_log, q=q)
        cprint(f'cable: {process_cable}', to_log=to_log, q=q)
        cprint(f'internet: {process_internet}', to_log=to_log, q=q)
        cprint(f'parent of cable: {psutil.Process(process_cable.pid).ppid()}', to_log=to_log, q=q)


if __name__ == "__main__":
    prompt_to_acquire_admin_rights_and_exit()
    sys.stderr = sys.stdout
    colorama.init(convert=False)
    mp.freeze_support()
    my_parser = argparse.ArgumentParser(add_help=True)
    # If user doesn't provide a name or an url for the miner, the script will use the default
    my_parser.add_argument('--color', type=str2bool, action='store', const=True, nargs='?', required=False,
                           default=True,
                           help="Default is False (Colorized text only in python interpreter)."
                                "If True, then the color will be displayed in cmd")
    my_parser.add_argument('--exe', type=str, action='store', required=False, default=get_name_of_current_exe(),
                           help='If you use get_name_of_current_exe() and run the exe through a bat file, '
                                'the function'
                                'kill_other_instances does not work, probably due to different path to the exe. '
                                'Use the argument and pass the name of the exe, in order to work though the bat file. '
                                'Do not forget that the argument is case sensitive'
                                'Example: --exe miner_API.exe.'
                                'If you do not use a bat file, it will work')
    my_parser.add_argument('--miner', action='store', type=str, required=False, default='miner')
    my_parser.add_argument('--stratumproxy', action='store', type=str, required=False, default='ErgoStratumProxy')
    my_parser.add_argument('--url_for_http', action='store', type=str, required=False,
                           default='http://127.0.0.1:36207/',
                           help='Specify the http url of the API. Requests module needs HTTP. '
                                'Default: http://127.0.0.1:36207/')
    my_parser.add_argument('--retries', action='store', type=int, required=False, default=5,
                           help='Specify the number of checking the hashrate retries '
                                'before the miner be killed and the bat initiatites. Default: 5')
    my_parser.add_argument('--retry_sec', action='store', type=int, required=False, default=5,
                           help="Specify the seconds for the program to wait until retries connecting"
                                " to the miner\'s API."
                                " Default: 5")
    my_parser.add_argument('--targettotalhashrate', action='store', type=int, required=False, default=71,
                           help='Specify the target TOTAL hashrate, so as the miner to be killed below the target. '
                                'Default: 35')
    my_parser.add_argument('--verbose', action='store', type=str2bool, required=False, default=1,
                           help='Prints more verbose text. Default is True')
    my_parser.add_argument('--verbose_dev', action='store', type=str2bool, required=False, default=1,
                           help='Prints the output of the most program. Default is False')
    my_parser.add_argument('--log', type=str2bool, action='store', required=False, default=True,
                           help='Saves the logging output to a file')
    my_parser.add_argument('--logfile', type=str, required=False, default='logfile.txt',
                           help='Specify the name of the log file name')
    my_parser.add_argument('--wallet', type=str, required=True,
                           default='',
                           help='Specify the address of your wallet')  # TODO: Remove defaults
    my_parser.add_argument('--debug', action='store', type=str2bool, required=False, default=0,
                           help='If true, it prints various variables in order to debug')
    my_parser.add_argument('--bat_file', type=str, required=False, default='ergo.bat',
                           help='Specify the name of the bat_file of the miner')
    my_parser.add_argument('--pool', type=str, required=False, default='woolypooly',
                           help='Specify the name of pool to be called')
    my_parser.add_argument('--flypool_to_be_called', action='store', type=str2bool, required=False, default=1,
                           help='Specify if flypool\'s / ethermine api will be called')
    my_parser.add_argument('--mode', action='store', required=False, default='no_battery',
                           help='Choose between battery or no_battery')
    my_parser.add_argument('--nvidia_laptop', action='store', type=str2bool, required=False, default=0,
                           help='If True, the script will try to overclock the nvidia gpu according to core, memory '
                                'arguments passed')
    my_parser.add_argument('--nvidia', action='store', type=str2bool, required=False, default=True)
    # 1+ arguments with argparse
    # https://stackoverflow.com/questions/15753701/how-can-i-pass-a-list-as-a-command-line-argument-with-argparse
    my_parser.add_argument('--overclock_settings', action='store', nargs='+', type=float, required=False,
                           default=(349, 200),
                           help="The first argument is the memory offset and the second the core offset."
                                "Unfortunately, through this setting, you cannot set custom voltage.")
    my_parser.add_argument('--overclock', action='store', type=str, required=False, default='external',
                           help='Choices: '
                                '\n1) external: it uses the external overclocking exe'
                                '\n2) self: it uses the pynvraw module and its wrapper '
                                '(Currently, you cannot set the voltage through pynvraw)'
                                '\n3) None: No overclock')
    args = my_parser.parse_args()
    # Command line arguments
    wallet = args.wallet
    targettotalhashrate = args.targettotalhashrate
    retry_sec = args.retry_sec
    retries = args.retries
    exe_name = args.exe
    miner = args.miner
    stratumproxy = args.stratumproxy
    url = args.url_for_http
    Verbose_dev = str2bool(args.verbose_dev)
    Verbose = str2bool(args.verbose)
    color = str2bool(args.color)
    to_log = str2bool(args.log)
    debug = str2bool(args.debug)
    logfile = args.logfile
    bat_file = args.bat_file
    pool = args.pool
    flypool_to_be_called = str2bool(args.flypool_to_be_called)
    nvidia = str2bool(args.nvidia)
    overclock_settings = args.overclock_settings
    mode = args.mode
    overclock = args.overclock
    q = mp.Queue()
    # Logging
    # Call the function to return and save the string to a variable and then it will be passed to logging
    path_to_file = check_path(logfile=logfile, debug=debug, to_log=to_log, q=q, sole_output=True)
    # Sole_output is True only here so as not to have cprint() duplicates from other multi processes
    log_mode = check_filemode(path=path_to_file, logfile=logfile, debug=debug, sole_output=True, to_log=to_log, q=q)
    start_logging(path_to_file=path_to_file, log_mode=log_mode)
    # https://stackoverflow.com/questions/11274040/os-getcwd-vs-os-path-abspathos-path-dirname-file
    # Returns the directory in which the file/script is stored. In our case, probably due to multiprocessing,
    # it's a temporary dir.
    # os.getcwd does not return always the directory of the file.
    # path = os.path.abspath(os.path.dirname(__file__)) # If the script is converted to an exe,
    # this path is temporary dir.
    if debug:
        cprint(f'__main__:  os.path.dirname(__file__): {os.path.dirname(__file__)}', to_log=to_log, q=q)
    if '.py' in sys.argv[0].split('\\')[0]:
        path = os.path.abspath(os.path.dirname(__file__))
        if debug:
            cprint(f'__main__: It\'s probably running as a py script from {path}', to_log=to_log, q=q)
    else:
        path = sys.argv[0].split('\\')
        path = '\\'.join(path[:-1])
        if debug:
            cprint(f'__main__: It\'s probably running as an exe from {path}', to_log=to_log, q=q)
    # Create a dictionary with all the arguments. It will be converted to a json file in Main()
    arguments = {'retry_sec': retry_sec, 'wallet': wallet, 'retries': retries,
                 'targettotalhashrate': targettotalhashrate, 'exe_name': exe_name, 'miner': miner,
                 'stratumproxy': stratumproxy, 'URL': url, 'pool': pool,
                 'Verbose_dev': Verbose_dev, 'color': color, 'to_log': to_log, 'debug': debug, 'logfile': logfile,
                 'bat_file': bat_file, 'flexpool_to_be_called': flypool_to_be_called, 'path': path, 'q': q,
                 'nvidia': nvidia, 'mode': mode, "overclock_settings": overclock_settings, 'overclock': overclock}
    main(arguments)
    while True:
        try:
            print(q.get())
        # Import the exception as docs point: https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues
        except queue.Empty:
            pass
