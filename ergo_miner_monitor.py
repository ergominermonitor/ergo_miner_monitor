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
from processes.cable_process import check_if_power_cable_is_plugged
from processes.other_instances import kill_other_instances

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
