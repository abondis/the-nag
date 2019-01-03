import pymsgbox
import time
import datetime

SLEEP = 600


def popup(f):
    answer = (
        pymsgbox.prompt('what are you doing now ?')
        or "NO ANSWER"
    ) + "\n"
    date = str(datetime.datetime.now()) + " : "
    f.write(date + answer)


with open('log', 'a', buffering=1) as f:
    while True:
        popup(f)
        time.sleep(SLEEP)
