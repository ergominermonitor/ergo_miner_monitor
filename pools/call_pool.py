import re,  time
from datetime import datetime
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pools.call_flypool_api import call_flypool_api
from helper_functions import headers, trace_error, cprint


def call_pool(pool='herominers', wallet='', debug=False, to_log=True, q=''):
    """
    It calls the pool's API or scrapes the pool's site for information (depends on the pool).

    :param pool: str: Pool's name
    :param wallet: str: Your wallet
    :param debug: Boolean
    :param to_log: Boolean
    :param q: The Queue object
    :return: Info from either the pool's API or pool's site

    Uses selenium (https://sites.google.com/chromium.org/driver/)
    """
    hashrate_3h = ''
    hashrate_24h = ''
    payment = ""
    pool = pool.lower().strip()
    wallet = wallet.strip()
    start = datetime.now()
    driver = None
    if debug:
        cprint(f"call_pool> pool: {pool} wallet: {wallet}", to_log=to_log, q=q)
    if pool == 'woolypooly':
        base_woolypooly_url = 'https://woolypooly.com/en/coin/erg/wallet/'
        woolypooly_url = base_woolypooly_url + wallet
        if debug:
            cprint(f'Wallet url: \n{woolypooly_url}', to_log=to_log, q=q)
        # Try first with Firefox
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument(
                f"user-agent={headers(debug=debug)['User-Agent']}")
            options.add_argument('--headless')
            driver = webdriver.Firefox(options=options)
            driver.get(woolypooly_url)
            time.sleep(3)
            htmlSource = driver.page_source
            soup = BeautifulSoup(htmlSource, "html.parser")
            try:
                for number, b in enumerate(soup.find_all('span', class_="tooltiptext")):
                    if number == 0:
                        hashrate_list = re.findall("[\?0-9]+\.*[0-9]*", b.text)  # TODO: Take into account kh/s
                        hashrate_3h, hashrate_24h = hashrate_list[1], hashrate_list[-1]
                    elif number == 2:
                        payment_list = re.findall("[0-9]+\.[0-9]*", b.text)
                        payment = payment_list[0]
                        # print(b.text)
            except Exception as err:
                trace_error(to_log=to_log, q=q)
            if debug:
                cprint(hashrate_3h, to_log=to_log, q=q)
                cprint(hashrate_24h, to_log=to_log, q=q)
                cprint(payment, to_log=to_log, q=q)
            driver.quit()
            # Convert all to float type. Catch the exception to the strings containing "?".
            try:
                hashrate_3h = float(hashrate_3h)
            except (ValueError, Exception) as err:
                if debug:
                    cprint(f"call_pool> Error in converting hashrate_3h variable: {err}", to_log=to_log, q=q)
            try:
                hashrate_24h = float(hashrate_24h)
            except (ValueError, Exception) as err:
                if debug:
                    cprint(f"call_pool> Error in converting hashrate_24h variable: {err}", to_log=to_log, q=q)
            try:
                payment = float(payment)
            except (ValueError, Exception) as err:
                if debug:
                    cprint(f"call_pool> Error in converting payment variable: {err}", to_log=to_log, q=q)
            return hashrate_3h, hashrate_24h, payment
        except selenium.common.exceptions.WebDriverException as err:
            if not debug:
                cprint(f"Firefox not found", to_log=to_log, q=q)
            elif debug:
                cprint(f"Firefox not found: {err}", to_log=to_log, q=q)
            # Try with Chrome
            try:
                options = webdriver.ChromeOptions()
                options.add_argument(
                    f"user-agent={headers()['User-Agent']}")
                options.add_argument("start-maximized")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--headless')
                driver = webdriver.Chrome(options=options)
                driver.get(woolypooly_url)
                time.sleep(0.25)
                htmlSource = driver.page_source
                soup = BeautifulSoup(htmlSource, "html.parser")
                try:
                    for number, b in enumerate(soup.find_all('span', class_="tooltiptext")):
                        if number == 0:
                            # print(b.text)
                            hashrate_list = re.findall("[\?0-9]+\.[0-9]*", b.text)
                            hashrate_3h, hashrate_24h = hashrate_list[0], hashrate_list[1]
                        elif number == 2:
                            payment_list = re.findall("[0-9]+\.[0-9]*", b.text)
                            payment = payment_list[0]
                            # print(b.text)
                except Exception as err:
                    raise err
                driver.quit()
                # Convert all to float type. Catch the exception of the strings containing "?".
                try:
                    hashrate_3h = float(hashrate_3h)
                except (ValueError, Exception) as err:
                    if debug:
                        cprint(f"call_pool> Error in converting hashrate_3h variable: {err}", to_log=to_log, q=q)
                try:
                    hashrate_24h = float(hashrate_24h)
                except (ValueError, Exception) as err:
                    if debug:
                        cprint(f"call_pool> Error in converting hashrate_24h variable: {err}", to_log=to_log, q=q)
                try:
                    payment = float(payment)
                except (ValueError, Exception) as err:
                    if debug:
                        cprint(f"call_pool> Error in converting payment variable: {err}", to_log=to_log, q=q)
                return hashrate_3h, hashrate_24h, payment
            except (selenium.common.exceptions.WebDriverException, Exception) as err:
                cprint(f"Cannot access either Chrome or Firefox in order to connect to WoolyPooly: {err}",
                       to_log=to_log, q=q)
    elif pool in ('flypool', 'ethermine'):
        text = call_flypool_api(wallet=wallet, flypool_to_be_called=True, to_log=to_log, q=q, debug=debug)
        return text
    elif pool == "herominers":
        herominers_base_url = "https://ergo.herominers.com/"
        # Firefox first
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument('--headless')
            driver = webdriver.Firefox(options=options)
            driver.get(herominers_base_url)
            time.sleep(3)
            #  Copy the CSS path from Firefox.
            #  Just select the element, right click -> Inspect -> Right click on the inspector output -> Copy -> CSS selector
            # https://stackoverflow.com/questions/71057617/how-to-insert-some-text-within-the-input-using-selenium-and-python
            WebDriverWait(driver, timeout=30).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "#page-body.night div.container div#page div#workerStats div.input-group input#yourStatsInput[placeholder='Enter Your Address']"))).send_keys(
                f"{wallet}")
            button = driver.find_element(By.CSS_SELECTOR,
                                         "#page-body.night div.container div#page div#workerStats div.input-group span.input-group-btn button#lookUp.btn.btn-default")
            button.click()
            time.sleep(1)  # Wait for the page to load
            current_hashrate_element = driver.find_element(By.CSS_SELECTOR,
                                                           "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div.statsbottomuserstats span#yourHashrateHolder.statstext2")
            current_hashrate = current_hashrate_element.text
            hashrate_1h_element = driver.find_element(By.CSS_SELECTOR,
                                                      "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#minerAvgHR div.statsbottomuserstats span span#yourHR1h.statstext2")
            hashrate_1h = hashrate_1h_element.text
            hashrate_6h_element = driver.find_element(By.CSS_SELECTOR,
                                                      "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#minerAvgHR div.statsbottomuserstats span span#yourHR6h.statstext2")
            hashrate_6h = hashrate_6h_element.text
            hashrate_24h_element = driver.find_element(By.CSS_SELECTOR,
                                                       "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#minerAvgHR div.statsbottomuserstats span span#yourHR24h.statstext2")
            hashrate_24h = hashrate_24h_element.text
            valid_shares_element = driver.find_element(By.CSS_SELECTOR,
                                                       "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#poolSharesShowHide div.statsbottomuserstats span#yourShares_good.statstext2")
            valid_shares = valid_shares_element.text
            stale_shares_element = driver.find_element(By.CSS_SELECTOR,
                                                       "html body#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#poolSharesShowHide div.statsbottomuserstats span#yourShares_stale.statstext2")
            stale_shares = stale_shares_element.text
            invalid_shares_element = driver.find_element(By.CSS_SELECTOR,
                                                         "html body#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#poolSharesShowHide div.statsbottomuserstats span#yourShares_invalid.statstext2")
            invalid_shares = invalid_shares_element.text
            pending_balanace_element = driver.find_element(By.CSS_SELECTOR,
                                                           "html body#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div.statsbottomuserstats a.statstext2.userpendingBalance span#yourPendingBalance")
            pending_balance = pending_balanace_element.text
            driver.quit()
            return current_hashrate, hashrate_1h, hashrate_6h, hashrate_24h, valid_shares, stale_shares, invalid_shares, pending_balance
        except (selenium.common.exceptions.WebDriverException, selenium.common.exceptions.SessionNotCreatedException,
                Exception) as err:
            trace_error(to_log=to_log, q=q, to_print_error=False)
            if not debug:
                cprint("Firefox probably not found. Trying with Chrome", to_log=to_log, q=q)
            elif debug:
                cprint(f"Firefox probably not found. Trying with Chrome.\tError: {err}", to_log=to_log, q=q)
            try:  # Quit Firefox
                driver.quit()
            # If driver is None due to another error, so driver=None and driver.quit() is not valid.
            except AttributeError:
                pass
            except (selenium.common.exceptions.WebDriverException, Exception) as err:
                trace_error(to_log=to_log, q=q, to_print_error=False)
            # Try with Chrome
            try:
                options = webdriver.ChromeOptions()
                options.add_argument(
                    f"user-agent={headers()['User-Agent']}")
                options.add_argument("start-maximized")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--headless')
                driver = webdriver.Chrome(options=options)
                driver.get(herominers_base_url)
                time.sleep(0.25)
                WebDriverWait(driver, timeout=20).until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "#page-body.night div.container div#page div#workerStats div.input-group input#yourStatsInput[placeholder='Enter Your Address']"))).send_keys(
                    f"{wallet}")
                button = driver.find_element(By.CSS_SELECTOR,
                                             "#page-body.night div.container div#page div#workerStats div.input-group span.input-group-btn button#lookUp.btn.btn-default")
                button.click()
                time.sleep(1)  # Wait for the page to load
                current_hashrate_element = driver.find_element(By.CSS_SELECTOR,
                                                               "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div.statsbottomuserstats span#yourHashrateHolder.statstext2")
                current_hashrate = current_hashrate_element.text
                hashrate_1h_element = driver.find_element(By.CSS_SELECTOR,
                                                          "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#minerAvgHR div.statsbottomuserstats span span#yourHR1h.statstext2")
                hashrate_1h = hashrate_1h_element.text
                hashrate_6h_element = driver.find_element(By.CSS_SELECTOR,
                                                          "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#minerAvgHR div.statsbottomuserstats span span#yourHR6h.statstext2")
                hashrate_6h = hashrate_6h_element.text
                hashrate_24h_element = driver.find_element(By.CSS_SELECTOR,
                                                           "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#minerAvgHR div.statsbottomuserstats span span#yourHR24h.statstext2")
                hashrate_24h = hashrate_24h_element.text
                valid_shares_element = driver.find_element(By.CSS_SELECTOR,
                                                           "#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#poolSharesShowHide div.statsbottomuserstats span#yourShares_good.statstext2")
                valid_shares = valid_shares_element.text
                stale_shares_element = driver.find_element(By.CSS_SELECTOR,
                                                           "html body#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#poolSharesShowHide div.statsbottomuserstats span#yourShares_stale.statstext2")
                stale_shares = stale_shares_element.text
                invalid_shares_element = driver.find_element(By.CSS_SELECTOR,
                                                             "html body#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div#poolSharesShowHide div.statsbottomuserstats span#yourShares_invalid.statstext2")
                invalid_shares = invalid_shares_element.text
                pending_balanace_element = driver.find_element(By.CSS_SELECTOR,
                                                               "html body#page-body.night div.container div#page div#workerStats div.yourStats.push-up-20 div.row.card div.col-md-6.col-sm-6 div.statsbottomuserstats a.statstext2.userpendingBalance span#yourPendingBalance")
                pending_balance = pending_balanace_element.text
                driver.quit()
                return current_hashrate, hashrate_1h, hashrate_6h, hashrate_24h, valid_shares, stale_shares, invalid_shares, pending_balance
            except (selenium.common.exceptions.WebDriverException,
                    selenium.common.exceptions.SessionNotCreatedException,
                    Exception) as err:
                cprint(f"Cannot access either Chrome or Firefox in order to connect to herominers: {err}",
                       to_log=to_log, q=q)
                trace_error(to_log=to_log, q=q, to_print_error=False)
                try:  # Quit Chrome
                    driver.quit()
                except (selenium.common.exceptions.WebDriverException, Exception):
                    trace_error(to_log=to_log, q=q)

    else:
        cprint("No pool was passed", to_log=to_log, q=q)
    end = datetime.now()
    if debug:
        cprint(f'{end - start}')