This is a POC implementation of the BREACH attack, in the simplified circumstances presented for this project.
The authors of this solution are:
  - Carlos Santamaría
  - Irene Quintana
  - Guillermo Fernández
  - Alvaro Clemente (Captain)

This implementation guesses a secret, one character at a time, and for every character,
tries all posible hex characters and selects the one that produces the shortest response.
To reduce the effect of Huffman Coding on the oracle, we add padding between the current
guess and the dictionary, and after the dictionary (to buffer the end of the dictionary with
anything that might be after in the request). 
Even with this techniques, sometimes we get some wrong guesses that have the same length as the
right ones. To solve these conflicts, we re-try this same algorithm using only the conflicted 
characters with a new random padding length. We do this a number of times, and eventually the
correct guess shows as the only winner. 

We present 2 programs that implement this algorithm, but one does it secuentially (breach-poc.py)
and the other parallelizes the requests for every guess using 16 Threads (one for every possible 
hexadecimal character). This way, we can reduce the guess time (for the https://malbot.net/poc/ 
token) from ~90s to 8s.

The program also allows to change some default values, to test it for other possible websites.
    - Padding Character. The default padding character used is '@'.
    - URL: The default url is "http://malbot.net/poc?request_token='"
    - Proxies: A flag that activates the use of http/https proxies, to see the requests with
    a program like Fiddler. (In case of activation, the proxy is http://127.0.0.1:8888 and 
    https://127.0.0.1:8888, the default proxies in Fiddler)

To see the help for the use of these programs, run `breach-poc.py -h` or `breach-parallel.py -h`.
