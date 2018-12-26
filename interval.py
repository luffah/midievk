"""
decorator function for looping
"""
import threading


def setInterval(function):
    def wrapper(*args, **kwargs):
        stopped = threading.Event()

        def loop():  # executed in another thread
            while not stopped.wait(0):  # until stopped
                function(*args, **kwargs)

        t = threading.Thread(target=loop)
        t.daemon = True  # stop if the program exits
        t.start()
        return stopped
    return wrapper
