import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.hevyapp.com"


class HevyClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("HEVY_API_KEY")
        if not self.api_key:
            raise ValueError("HEVY_API_KEY is required")
        self.session = requests.Session()
        self.session.headers.update({"api-key": self.api_key})

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{BASE_URL}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_workouts(self, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        return self._get("/v1/workouts", params={"page": page, "pageSize": page_size})

    def get_workout(self, workout_id: str) -> dict[str, Any]:
        return self._get(f"/v1/workouts/{workout_id}")

    def fetch_all_workouts(self, page_size: int = 10) -> list[dict[str, Any]]:
        first_page = self.list_workouts(page=1, page_size=page_size)
        workouts = first_page.get("workouts", [])
        page_count = first_page.get("page_count", 1)

        for page in range(2, page_count + 1):
            resp = self.list_workouts(page=page, page_size=page_size)
            workouts.extend(resp.get("workouts", []))

        return workouts
