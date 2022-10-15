import os
import time
import psutil
from colorama import Fore, Style
from helper_functions import get_name_of_current_exe, str2bool, cprint, findAllProcessesRunning, trace_error


def kill_other_instances(name="", to_log=True, Verbose=True, main_parent_pid='',
                         debug=False, q=''):
    """
    If there are any other instances, it tries to kill them (Child & Parent processes)
    It traces and kills standalone .exe with the same name or python.exe, when running as a .py script.
    If the exe is a python.exe, it will kill all other python.exe running at the moment.
    :param name: If not given, it's the name of the current exe.
    :return: None
    """
    process_list = []
    if name == "" or None:
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
        trace_error(to_log=to_log, q=q)
        cprint(f"Killing_other_instances Function error due to {err}", to_log=to_log, q=q)
