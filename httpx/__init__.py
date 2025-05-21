import json as json_module
import types
import typing
from urllib.parse import urljoin, urlparse, urlencode

class URL:
    def __init__(self, url: str):
        self._url = url
        p = urlparse(url)
        self.scheme = p.scheme
        netloc = (p.hostname or "") + (f":{p.port}" if p.port else "")
        self.netloc = netloc.encode()
        self.path = p.path
        self.raw_path = p.path.encode()
        self.query = p.query.encode()

    def join(self, url: str) -> "URL":
        return URL(urljoin(self.__str__(), url))

    def __str__(self) -> str:
        return self._url


class ByteStream:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class Request:
    def __init__(self, method: str, url: URL, headers: typing.Dict[str, str] | None = None, content: bytes | None = None):
        self.method = method.upper()
        self.url = url if isinstance(url, URL) else URL(url)
        self.headers = headers or {}
        self._content = content or b""

    def read(self) -> bytes:
        return self._content


class Response:
    def __init__(self, status_code: int = 200, headers: typing.Iterable[tuple[str, str]] | None = None, stream: ByteStream | None = None, request: Request | None = None):
        self.status_code = status_code
        self.headers = dict(headers or [])
        self.stream = stream or ByteStream(b"")
        self.request = request

    def read(self) -> bytes:
        return self.stream.read()

    @property
    def text(self) -> str:
        return self.read().decode()

    def json(self) -> typing.Any:
        return json_module.loads(self.text or "null")


class BaseTransport:
    def handle_request(self, request: Request) -> Response:  # pragma: no cover - interface
        raise NotImplementedError


class Client:
    def __init__(self, *, app=None, base_url: str = "http://testserver", headers: dict | None = None, transport: BaseTransport | None = None, follow_redirects: bool = True, cookies=None):
        self.base_url = URL(base_url)
        self.headers = headers or {}
        self.transport = transport
        self.cookies = cookies or {}
        self.follow_redirects = follow_redirects

    def _build_url(self, url: str | URL) -> URL:
        if isinstance(url, URL):
            return url
        if url.startswith("http://") or url.startswith("https://"):
            return URL(url)
        return self.base_url.join(url)

    def request(self, method: str, url: str | URL, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=None, follow_redirects=None, timeout=None, extensions=None):
        body = b""
        all_headers = {**self.headers}
        if headers:
            all_headers.update(headers)
        if json is not None:
            body = json_module.dumps(json).encode()
            all_headers.setdefault("content-type", "application/json")
        elif data is not None:
            if isinstance(data, dict):
                body = urlencode(data).encode()
                all_headers.setdefault("content-type", "application/x-www-form-urlencoded")
            else:
                body = data if isinstance(data, (bytes, bytearray)) else str(data).encode()
        elif content is not None:
            body = content if isinstance(content, (bytes, bytearray)) else str(content).encode()
        request = Request(method, self._build_url(url), headers=all_headers, content=body)
        assert self.transport is not None, "Transport required"
        return self.transport.handle_request(request)

    def get(self, url: str | URL, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str | URL, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str | URL, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str | URL, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str | URL, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str | URL, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str | URL, **kwargs):
        return self.request("OPTIONS", url, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


# Submodules used only for typing annotations in Starlette
import sys
_types = types.SimpleNamespace(
    URLTypes=typing.Any,
    RequestContent=typing.Any,
    RequestFiles=typing.Any,
    QueryParamTypes=typing.Any,
    HeaderTypes=typing.Any,
    CookieTypes=typing.Any,
    AuthTypes=typing.Any,
)
sys.modules[__name__ + "._types"] = _types

_client = types.SimpleNamespace(
    USE_CLIENT_DEFAULT=object(),
    CookieTypes=typing.Any,
    TimeoutTypes=typing.Any,
    UseClientDefault=typing.Any,
)
sys.modules[__name__ + "._client"] = _client
