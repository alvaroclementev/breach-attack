import argparse

VAR_1 = 1
PADDING_CHAR = '@'

VAR_2 = [1, 2, 3]

if __name__ == '__main__':
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--proxy', action='store_true',
            help='''Use the internal proxy to inspect on fiddler. The proxies by default are:
"http://127.0.0.1:8888"
"https://127.0.0.1:8888"''')
    parser.add_argument('--padding', type=str, default='@',
            help="Use a custom character or string to pad the requests (default is '@')")

    args = parser.parse_args()

    print(f'The args are: {args}')
    if args.proxy:
        print('The proxy flag was detected!')
        VAR_1 = 2

    if args.padding != '@':
        PADDING_CHAR = args.padding
        print(f'The padding char was changed to {PADDING_CHAR}')

    print(f'The value of the variables is VAR_1 = {VAR_1} and VAR_2 = {VAR_2}')
