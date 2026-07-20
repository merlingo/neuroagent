import signal
import time


def main() -> None:
    print("NeuroAgent worker scheduler started (idle — no tasks configured).")
    stop = False

    def _handle(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    while not stop:
        time.sleep(60)

    print("NeuroAgent worker scheduler shutting down.")


if __name__ == "__main__":
    main()
