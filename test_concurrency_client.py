import requests
import threading
import time

def call_block():
    print("Requesting /block...")
    start = time.time()
    try:
        r = requests.get("http://localhost:8085/block")
        print(f"/block finished in {time.time() - start:.2f}s: {r.text}")
    except Exception as e:
        print(f"/block error: {e}")

def call_ping():
    time.sleep(1) # Wait a bit to ensure block is running
    print("Requesting /ping...")
    start = time.time()
    try:
        r = requests.get("http://localhost:8085/ping", timeout=2)
        print(f"/ping finished in {time.time() - start:.2f}s: {r.text}")
    except Exception as e:
        print(f"/ping error: {e}")

t1 = threading.Thread(target=call_block)
t2 = threading.Thread(target=call_ping)

t1.start()
t2.start()

t1.join()
t2.join()
