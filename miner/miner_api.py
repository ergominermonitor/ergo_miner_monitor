import json
import requests
from helper_functions import trace_error, cprint


def get_infos(url='http://127.0.0.1:36207/', debug=False, to_log=True, q=''):
    """Returns the information from miner's API as a dictionary containing a tuple for each gpu"""
    infos = {}
    try:
        page = requests.get(url)
    #  https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as err:
        trace_error(to_log=to_log, q=q)
        if not debug:
            cprint("Error in connecting to miner\'s API", to_log=to_log, q=q)
        if debug:
            cprint(f"Error in miner\'s API: {err}", to_log=to_log, q=q)
        return None
    try:
        json_data = json.loads(page.text)  # String to json (In python json is a dictionary)
        for number, a in enumerate(json_data['devices']):
            gpu_name = json_data['devices'][0]['devname']
            pci_id = json_data['devices'][0]['pciid']
            hashrate = json_data['devices'][0]['hashrate']
            power = json_data['devices'][0]['power']
            temperature = json_data['devices'][0]['temperature']
            total_hashrate = json_data['total']
            total_time = json_data['uptime']
            infos[f'gpu{number}'] = (gpu_name, pci_id, hashrate, power, temperature, total_hashrate, total_time)
        if len(infos) != 0:
            return infos
        else:
            return None
    except Exception as err:
        trace_error(to_log=to_log, q=q)
        cprint(f'Error in get_infos function: {err}', to_log=to_log, q=q)
        return None
