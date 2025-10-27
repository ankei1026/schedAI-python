import requests

class LaravelAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, endpoint: str):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
