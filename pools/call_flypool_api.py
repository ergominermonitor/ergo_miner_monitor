import decimal
import requests
from colorama import Fore, Style
from helper_functions import cprint


def call_flypool_api(wallet='', flypool_to_be_called=True, to_log=True, q='', debug=False):
    """
    Calls flypool's API based on wallet passed.
    :param wallet: str: The Wallet
    :param flypool_to_be_called:
    :param to_log: Boolean
    :param q: The Queue object
    :param debug: Boolean
    :return: str: Info from Flypool's API
    """
    if flypool_to_be_called:
        url_workers = f"https://api-ergo.flypool.org/miner/{wallet}/dashboard"
        try:
            pool_workers = requests.get(url_workers)
            pool_workers = pool_workers.json()
            worker_dict = {}
            if debug:
                cprint(pool_workers,
                       to_log=to_log, q=q)
            if pool_workers['status'] in ("ok", "OK", "Ok", "oK") and len(pool_workers['data']['statistics']) != 0:
                result_dict = pool_workers["data"]['workers']
                for worker in result_dict:
                    name = worker['worker']
                    worker_dict[name] = {}
                    worker_dict[name]['reportedHashrate'] = round(int(worker['reportedHashrate']) / 1000000, 4)
                    worker_dict[name]['currentHashrate'] = round(
                        int(worker['currentHashrate']) / 1000000, 4)
                    worker_dict[name]['valid_shares'] = worker['validShares']
                    worker_dict[name]['stale_shares'] = worker['staleShares']
                    worker_dict[name]['invalid_shares'] = worker['invalidShares']
                    worker_dict[name]['stale_ratio'] = round(decimal.Decimal(
                        float(worker_dict[name]['stale_shares']) / float(worker_dict[name]['valid_shares'])), 4) * 100
                if debug:
                    cprint(worker_dict,
                           to_log=to_log, q=q)
                pool_statistics = pool_workers["data"]["currentStatistics"]
                reported_hashrate = str(round(pool_statistics['reportedHashrate'] / 1000000, 4))
                current_effective_hashrate = str(round(pool_statistics['currentHashrate'] / 1000000, 4))
                if debug:
                    cprint(pool_workers)
                    cprint(
                        f'Pool: Reported / Current hashrate: {reported_hashrate} || {current_effective_hashrate}'
                        f' MH/s )',
                        to_log=to_log, q=q)
                text = f'\n{22 * " "}Pool: Flypool' \
                       f'\n{22 * " "}{len("Pool: ") * " "}Reported / Current hashrate: {reported_hashrate} || {current_effective_hashrate}' \
                       f' MH/s'
                valid_shares = pool_statistics['validShares']
                stale_shares = pool_statistics['staleShares']
                invalid_shares = pool_statistics['invalidShares']
                if debug:
                    cprint(f'Pool: Valid/Stale/Invalid shares: {valid_shares}/{stale_shares}/{invalid_shares}',
                           to_log=to_log,
                           q=q)
                text = text + f'\n{22 * " "}{len("Pool: ") * " "}Valid/Stale/Invalid shares: {valid_shares}/{stale_shares}/{invalid_shares}'
                stale_ratio = round(float(pool_statistics['staleShares']) / float(pool_statistics['validShares']),
                                    4) * 100
                # Display the rounded number up to 2 decimal {:0.2f}; workaround for the floating number problem
                if debug:
                    cprint(f'Pool: stale ratio {stale_ratio:0.2f}%', to_log=to_log, q=q)
                    cprint(f'Workers:', to_log=to_log, q=q)
                text = text + f'\n{22 * " "}{len("Pool: ") * " "}stale ratio {stale_ratio:0.2f}%' + \
                       f'\n{22 * " "}Workers:'
                for number, worker in enumerate(worker_dict):
                    if debug:
                        cprint(
                            f'{22 * " "}\t{number + 1}){worker}: Valid/Stale/Invalid shares: {worker_dict[worker]["valid_shares"]}/{worker_dict[worker]["stale_shares"]}/{worker_dict[worker]["invalid_shares"]} --- Stale ratio: {worker_dict[worker]["stale_ratio"]:0.2f}%',
                            to_log=to_log, q=q)
                    text = text + f'\n{22 * " "}\t{number + 1}){worker}: Valid/Stale/Invalid shares: {worker_dict[worker]["valid_shares"]}/{worker_dict[worker]["stale_shares"]}/{worker_dict[worker]["invalid_shares"]} --- Stale ratio: {worker_dict[worker]["stale_ratio"]:0.2f}%'
                    if number + 1 < 10:  # To be printed symmetrically
                        if debug:
                            cprint(
                                f'{22 * " "}\t  {len(worker) * " "}  Reported / Current Hashrate: {worker_dict[worker]["reportedHashrate"]} / {worker_dict[worker]["currentHashrate"]}  MH/s',
                                to_log=to_log, q=q)
                        text = text + f'\n{22 * " "}\t  {len(worker) * " "}  Reported / Current Hashrate: {worker_dict[worker]["reportedHashrate"]} / {worker_dict[worker]["currentHashrate"]}  MH/s'
                    else:  # A space is added in front of {worker}
                        if debug:
                            cprint(
                                f'\t   {len(worker) * " "}  Reported / Current Hashrate: {worker_dict[worker]["reportedHashrate"]} / {worker_dict[worker]["currentHashrate"]} MH/s',
                                to_log=to_log, q=q)
                        text = text + f'\n\t   {len(worker) * " "}  Reported / Current Hashrate: {worker_dict[worker]["reportedHashrate"]} / {worker_dict[worker]["currentHashrate"]} MH/s'
                # print(text)
                return text
            else:
                return f'\nWallet ({wallet}) has no workers connected to pool.'
        except Exception as err:
            cprint(f"{Fore.RED}Error in pool's Api: {Fore.LIGHTRED_EX}{err}{Style.RESET_ALL}", to_log=to_log, q=q)