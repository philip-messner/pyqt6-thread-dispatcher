import queue


def test1():
    q = queue.Queue()
    q2 = queue.PriorityQueue()

    print(isinstance(q, queue.Queue), isinstance(q, queue.PriorityQueue))
    print(isinstance(q2, queue.Queue), isinstance(q2, queue.PriorityQueue))
    print(q.qsize())

if __name__ == '__main__':
    test1()