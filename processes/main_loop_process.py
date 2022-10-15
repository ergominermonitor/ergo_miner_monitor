import decimal
import itertools
import json
import os
import sys
import time
from datetime import datetime
import colorama
import psutil
from colorama import Fore, Style, Back
import nvidia_gpu
from helper_functions import str2bool, cprint, get_name_of_current_exe, checkIfProcessRunning, exe_name_of_miner, \
    killiftheprocess, start_the_miner, start_the_oc_bat_file, countdown_to_restart_whole_process, trace_error, \
    get_current_time
from logger_ import check_path, start_logging, check_filemode
from miner.miner_api import get_infos
from pools.call_flypool_api import call_flypool_api
from pools.call_pool import call_pool
from processes.other_instances import kill_other_instances


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
    with open(os.path.join(path, '../arguments.json'), 'r', encoding='utf-8') as file:
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
