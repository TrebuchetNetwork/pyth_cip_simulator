import asyncio
import os
import signal
import sys
import time
from collections import deque
from typing import List, Any, Dict, Deque
from loguru import logger
from pythclient.solana import PYTHNET_HTTP_ENDPOINT, PYTHNET_WS_ENDPOINT
from pythclient.pythclient import PythClient
from pythclient.ratelimit import RateLimit
from pythclient.pythaccounts import PythPriceAccount, PythPriceInfo
from pythclient.utils import get_key

logger.enable("pythclient")
RateLimit.configure_default_ratelimit(overall_cps=9, method_cps=3, connection_cps=3)

to_exit = False
previous_stakes = {}  # Dictionary to track previous stakes for each publisher

def set_to_exit(sig: Any, frame: Any):
    global to_exit
    to_exit = True

signal.signal(signal.SIGINT, set_to_exit)

async def main():
    global to_exit
    use_program = len(sys.argv) >= 2 and sys.argv[1] == "program"
    v2_first_mapping_account_key = get_key("pythnet", "mapping")
    v2_program_key = get_key("pythnet", "program")

    tracking_length = 15
    interval_duration = 4 # translates to 60s predictive window 15x4 = 40
    initial_stake = 100 # how many tokens are initially staked
    symbol_for_observation = "Crypto.BTC/USD"

    publisher_positions: Dict[str, Deque[PythPriceInfo]] = {}
    publisher_stakes: Dict[str, int] = {key: initial_stake for key in publisher_positions}
    publisher_win_rates: Dict[str, List[int]] = {}  # 1 for win, 0 for loss
    transaction_log_path = "transaction_log.txt"
    pythsensus_price_deque : Deque[PythPriceAccount] = deque(maxlen=tracking_length)

    async with PythClient(
        first_mapping_account_key=v2_first_mapping_account_key,
        program_key=v2_program_key if use_program else None,
        solana_endpoint=PYTHNET_HTTP_ENDPOINT,
        solana_ws_endpoint=PYTHNET_WS_ENDPOINT
    ) as client:
        await client.refresh_all_prices()
        products = await client.get_products()
        for product in products:
            if product.attrs['symbol'] != symbol_for_observation:
                continue
            prices = await product.get_prices()
            for _, price_account in prices.items():
                for component in price_account.price_components:
                    publisher_key = component.publisher_key.key
                    publisher_positions.setdefault(publisher_key, deque(maxlen=tracking_length))
                    publisher_stakes.setdefault(publisher_key, initial_stake)
                    publisher_win_rates.setdefault(publisher_key, [])

        while not to_exit:
            start_time = time.time()
            await client.refresh_all_prices()
            for product in products:
                if product.attrs['symbol'] != symbol_for_observation:
                    continue
                prices = await product.get_prices()
                for _, price_account in prices.items():
                    pythsensus_price_deque.append(price_account) # add the full object for later
                    for component in price_account.price_components:
                        publisher_key = component.publisher_key.key
                        price_info = component.latest_price_info
                        if price_info:
                            publisher_positions[publisher_key].append(price_info)
                    #calculate the next round
                    if len(publisher_positions[publisher_key]) == tracking_length:
                        evaluate_publishers(publisher_positions, publisher_stakes, publisher_win_rates, transaction_log_path, price_info, pythsensus_price_deque)

            end_time = time.time()
            loop_duration = end_time - start_time
            print("Ending duration in seconds " + str(loop_duration)+ " with escapement interval " +str(interval_duration)  )
            sleep_time = max(0, interval_duration - loop_duration)
            print("Sleeping for " + str(sleep_time))
            print("Symbol " + str(symbol_for_observation))
            await asyncio.sleep(sleep_time)

            display_publishers(publisher_stakes)



def evaluate_publishers(publisher_positions: Dict[str, Deque[PythPriceInfo]], stakes: Dict[str, int], win_rates: Dict[str, List[int]], transaction_log_path: str, last_price_info: PythPriceInfo, pythsensus_price_deque:Deque[PythPriceAccount]):
    prices = {key: positions[-1].price for key, positions in publisher_positions.items() if positions} #get all prices at T0
    sorted_publishers = sorted(prices.items(), key=lambda x: x[1], reverse=True) #sort all prices with publisher keys at T0
    pythsensus_price_current = last_price_info.price #get the price at T0+N or current price
    pythsensus_price_T0 = pythsensus_price_deque[-1].aggregate_price #get the price at T0

    total_price_components = len(sorted_publishers)

    while len(sorted_publishers) > 1: # we ignore the last remaining unmachted one for sake of simplcity
        max_publisher, max_price_t0 = sorted_publishers.pop(0) # get the max price outlier publisher
        min_publisher, min_price_t0 = sorted_publishers.pop(-1) # get the min price outlier publisher

        #max will always be long, min will always be short
        #so who was right? long or short?
        #depends on the difference between pythsensus_price_current and pythsensus_price_T0
        #who is the winner?
        direction_winner = "" #MAX or MIN
        if pythsensus_price_current > pythsensus_price_T0:
            #the longs have won since the new price is higher
            direction_winner = "MAX"
        else:
            #the shorts have won since the new price is lower
            direction_winner = "MIN"

        #calculate if winner did overshoot or undershoot too much , if submitted prices were too big then invert the winners
        deviation_max_publisher = abs(max_price_t0 - pythsensus_price_current)
        deviation_min_publisher = abs(min_price_t0 - pythsensus_price_current)

        winner = direction_winner #default
        directional_deviation_forgivness_factor = 0.5 # 50% extra factor if you get the direction right but you over/under shoot
        if winner == "MAX":
            if deviation_max_publisher*directional_deviation_forgivness_factor > deviation_min_publisher: #overshoot LONG
                winner = "MIN"
        else:
            if deviation_min_publisher*directional_deviation_forgivness_factor > deviation_max_publisher: #undershoot SHORT
                winner = "MAX"

        #exponential function
        penalty_exponent = exponential_penalty_function(len(sorted_publishers),total_price_components)

        #top reward calculation is based on the winning publisher stake to incentivise staking
        top_reward = 0
        top_penalty = 0
        if winner == "MAX":
            top_reward = penalty_exponent * stakes[max_publisher]
            top_penalty = penalty_exponent * stakes[min_publisher]
        else:
            top_reward = penalty_exponent * stakes[min_publisher]
            top_penalty = penalty_exponent * stakes[max_publisher]

        #transfer amount is however capped on max 1% per turn for biggest outliners going linearly to 0.01%
        transfer_amount = min(top_reward,top_penalty)

        #transactions simulation
        if winner == "MAX":
            stakes[max_publisher] += transfer_amount
            stakes[min_publisher] -= transfer_amount
        else:
            stakes[max_publisher] -= transfer_amount
            stakes[min_publisher] += transfer_amount

        with open(transaction_log_path, "a") as file:
            file.write(f"Transferred ${transfer_amount:.2f} from {min_publisher if winner == 'MAX' else max_publisher} to {max_publisher if winner == 'MAX' else min_publisher}. Max Bid at T0: ${max_price_t0:.2f}, Min Bid at T0: ${min_price_t0:.2f}. Current Aggregate Price: ${pythsensus_price_current:.2f}, Initial Aggregate Price: ${pythsensus_price_T0:.2f} , Penalty Exponent ${penalty_exponent:.6f}\n")



def display_publishers(stakes: Dict[str, int]):
    deltas = {}
    for publisher, current_stake in stakes.items():
        previous_stake = previous_stakes.get(publisher, current_stake)
        delta = current_stake - previous_stake
        deltas[publisher] = delta
        previous_stakes[publisher] = current_stake  # Update the record for next time

    # Sort publishers by deltas
    sorted_publishers = sorted(stakes.items(), key=lambda x: deltas[x[0]], reverse=True)

    print("\nTrebuchet Validator Publisher Balances:")
    for publisher, stake in sorted_publishers:
        delta = deltas[publisher]
        color = "\033[92m" if delta > 0 else "\033[91m" if delta < 0 else "\033[0m"
        delta_display = f"{color}{delta:+}\033[0m" if delta != 0 else f"{delta:+}"
        print(f"Publisher {publisher}: Stake = {stake} ({delta_display})")


def exponential_penalty_function(outlier_number,total_price_components):
    a = 0.0000001
    b = 10 ** (2 / total_price_components)
    y = a * (b ** (outlier_number - 1))
    return y

asyncio.run(main())
