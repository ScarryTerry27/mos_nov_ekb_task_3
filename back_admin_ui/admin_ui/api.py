from urllib.parse import urljoin
import httpx
from config import API_BASE_URL, DEFAULT_TIMEOUT


class ApiClient:
    def __init__(self, base_url: str = API_BASE_URL, token: str | None = None):
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True)

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ):
        r = self._client.request(
            method=method,
            url=self._url(path),
            params=params,
            json=json,
            data=data,
            files=files,
            headers=self._headers(),
        )
        r.raise_for_status()
        # 204/empty-body — вернём None
        if not r.content:
            return None
        ct = r.headers.get("content-type", "")
        return r.json() if ct.startswith("application/json") else r.text

    def get(self, path: str, params: dict | None = None):
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None):
        return self._request("POST", path, json=json)

    def post_multipart(self, path: str, files: dict, data: dict | None = None):
        return self._request("POST", path, data=data, files=files)

    def put(self, path: str, json: dict | None = None, params: dict | None = None):
        return self._request("PUT", path, params=params, json=json)

    def patch(self, path: str, json: dict | None = None, params: dict | None = None):
        return self._request("PATCH", path, params=params, json=json)

    def delete(self, path: str, params: dict | None = None):
        return self._request("DELETE", path, params=params)

    def close(self):
        self._client.close()
