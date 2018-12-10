import signal

def keyboardInterruptHandler(signal, frame):
    print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))
    exit(0)

signal.signal(signal.SIGINT, keyboardInterruptHandler)

while True:
    pass