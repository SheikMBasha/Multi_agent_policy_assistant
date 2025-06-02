import requests

class CalculateIncentiveTool:
    """Tool to call external API to calculate compensation, GAP refund, and funding address."""

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")  # Ensure no trailing slash

    def run(self, dealer_name: str) -> float:
        """Calls the compensation API and returns the compensation value."""
        print("Run method called in calculateincentivetool")
        print(f"Dealer name is {dealer_name}")
        url = f"{self.api_url}/calculate-compensation"
        params = {"dealerName": dealer_name}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()["compensation"]

    def get_gap_refund(self, dealer_name: str) -> float:
        """Calls a (new) endpoint to get GAP refund by dealer."""
        print("GAP refund method called")
        print(f"Dealer name is {dealer_name}")
        url = f"{self.api_url}/get-gap-refund"
        params = {"dealerName": dealer_name}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()["gapRefund"]

    def get_funding_address(self, rbc_number: str) -> str:
        """Calls a (new) endpoint to get funding address by RBC number."""
        print("Funding address method called")
        print(f"RBC number is {rbc_number}")
        url = f"{self.api_url}/get-funding-address"
        params = {"rbcNumber": rbc_number}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()["fundingAddress"]
