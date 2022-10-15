import os
import pathlib
import colorama
import multiprocessing as mp

import psutil
from colorama import Fore, Style
from helper_functions import str2bool, cprint, check_write_update_json_arguments
from processes.cable_process import check_if_power_cable_is_plugged
from processes.internet_connection_process import checking_internet_connection
from processes.main_loop_process import main_loop


def main(arguments):
    arguments = arguments
    path = pathlib.Path(arguments['path'])
    q = arguments['q']
    color = str2bool(arguments['color'])
    debug = str2bool(arguments['debug'])
    to_log = str2bool(arguments['to_log'])
    Verbose = arguments['Verbose']
    miner = arguments['miner']
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
    process_main_loop = mp.Process(target=main_loop, name='Main_Loop', args=(f'{arguments["retries"]}',
                                                                             f'{to_log}', f'{arguments["url"]}',
                                                                             f'{arguments["retry_sec"]}', f'{miner}',
                                                                             f'{arguments["stratumproxy"]}',
                                                                             f'{Verbose}',
                                                                             f'{arguments["Verbose_dev"]}',
                                                                             f'{arguments["targettotalhashrate"]}',
                                                                             f'{color}', f'{arguments["logfile"]}',
                                                                             f'{arguments["wallet"]}',
                                                                             f'{main_parent_pid}', f'{debug}',
                                                                             f'{arguments["bat_file"]}',
                                                                             f'{arguments["flypool_to_be_called"]}',
                                                                             q, f'{arguments["nvidia"]}',
                                                                             f'{arguments["pool"]}',
                                                                             f'{arguments["overclock_settings"]}',
                                                                             f'{arguments["overclock"]}', path
                                                                             ))
    process_cable = mp.Process(target=check_if_power_cable_is_plugged, name='Cable_checking',
                               args=(f'{color}', f'{arguments["logfile"]}', f'{str2bool(debug)}', False,
                                     f'{str2bool(to_log)}',
                                     q, path, f'{arguments["miner"]}', f'{arguments["stratumproxy"]}',
                                     f'{arguments["mode"]}'
                                     ))
    process_internet = mp.Process(target=checking_internet_connection, name='Internet_checking',
                                  args=(f'{color}', f'{arguments["logfile"]}', f'{str2bool(debug)}', False,
                                        f'{str2bool(to_log)}',
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
