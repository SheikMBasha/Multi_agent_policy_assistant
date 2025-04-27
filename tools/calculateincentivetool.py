import requests

class CalculateIncentiveTool:
    """Tool to call external API to calculate incentive."""

    def __init__(self, api_url: str):
        self.api_url = api_url

    def run(self, dealer_name: str) -> float:
        """Calls the API and returns the compensatoin value."""
        print("Run method called in calculateincentivetool")
        print(f"Dealer name is {dealer_name}")
        print(f"API url is {self.api_url}")
        params = {
            "dealerName": dealer_name
        }
        response = requests.get(self.api_url, params=params)
        response.raise_for_status()
        return response.json()["compensation"]
