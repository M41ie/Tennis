import multiprocessing
import time
import json
import urllib.request
import urllib.error
import importlib

import tennis.storage as storage

CACHE_KEY = "tennis:cache_version"

class SharedRedis:
    def __init__(self, store):
        self.store = store

    def get(self, key):
        value = self.store.get(key)
        if isinstance(value, int):
            return str(value).encode()
        return value

    def setex(self, key, ttl, value):
        if isinstance(value, bytes):
            self.store[key] = value
        else:
            self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)

    def incr(self, key):
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value


def run_server(port: int, store):
    import uvicorn
    importlib.reload(storage)
    storage._redis = SharedRedis(store)
    api = importlib.reload(importlib.import_module("tennis.api"))
    uvicorn.run(api.app, host="127.0.0.1", port=port, log_level="error")


def wait_for(fn, timeout=5.0, interval=0.1):
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(interval)
    return False


def server_ready(port):
    def check():
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/users/nonexist")
        except urllib.error.HTTPError as e:
            return e.code == 404
        except Exception:
            return False
        return True
    return wait_for(check, timeout=10)


def post_json(port, path, data):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_json(port, path):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def test_cache_version_sync(tmp_path):
    manager = multiprocessing.Manager()
    store = manager.dict()

    port1, port2 = 8001, 8002
    p1 = multiprocessing.Process(target=run_server, args=(port1, store))
    p2 = multiprocessing.Process(target=run_server, args=(port2, store))
    p1.start()
    p2.start()
    try:
        assert server_ready(port1)
        assert server_ready(port2)

        version_before = store.get(CACHE_KEY, 0)
        resp = post_json(
            port1,
            "/users",
            {"user_id": "u1", "name": "U1", "password": "pw"},
        )
        assert resp["status"] == "ok"

        def version_changed():
            return store.get(CACHE_KEY, 0) != version_before

        assert wait_for(version_changed, timeout=5)

        def user_available():
            try:
                data = get_json(port2, "/users/u1")
                return data.get("user_id") == "u1"
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return False
                raise
        assert wait_for(user_available, timeout=5)
    finally:
        p1.terminate()
        p2.terminate()
        p1.join(5)
        p2.join(5)
