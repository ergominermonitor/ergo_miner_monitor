###############################################################
# miner watchdog 16/10/22 => bug fixes, refactoring #
################################################################
import os, colorama, sys
import queue
import multiprocessing as mp
import argparse
from helper_functions import str2bool, cprint, prompt_to_acquire_admin_rights_and_exit, \
    get_name_of_current_exe, check_write_update_json_arguments
from main import main
from misc.logger_ import check_path, check_filemode, start_logging

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
                 'stratumproxy': stratumproxy, 'url': url, 'pool': pool, 'Verbose': Verbose,
                 'Verbose_dev': Verbose_dev, 'color': color, 'to_log': to_log, 'debug': debug, 'logfile': logfile,
                 'bat_file': bat_file, 'flypool_to_be_called': flypool_to_be_called, 'path': path, 'q': q,
                 'nvidia': nvidia, 'mode': mode, "overclock_settings": overclock_settings, 'overclock': overclock}
    main(arguments)
    while True:
        try:
            print(q.get())
        # Import the exception as docs point: https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues
        except queue.Empty:
            pass
