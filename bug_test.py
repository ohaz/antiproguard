__author__ = 'ohaz'
from concurrent.futures import ThreadPoolExecutor
threads = 4
to_read = [(1,2,3), (3,4,5), (6,6,7)]


def read_and_parse(path, f, start):
    print('In THREAD')

with ThreadPoolExecutor(max_workers=threads) as executor:
    for work in to_read:
        executor.submit(read_and_parse, work[0], work[1], work[2])

