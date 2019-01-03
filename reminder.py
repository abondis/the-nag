import pymsgbox
import time

SLEEP = 600


def popup(f):
    answer = (
        pymsgbox.prompt('what are you doing now ?')
        or "NO ANSWER"
    ) + "\n"
    f.write(answer)


with open('log', 'a', buffering=1) as f:
    while True:
        popup(f)
        time.sleep(SLEEP)
