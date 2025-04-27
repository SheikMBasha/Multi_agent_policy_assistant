from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()

# Sample dealer data
dealer_data = {
    "ford": 1500.00,
    "tesla": 1750.50,
    "honda": 1325.75,
}

@app.get("/calculate-incentive")
def calculate_incentive(
    contractAPR: float = Query(..., description="Contract APR"),
    buyRate: float = Query(..., description="Buy Rate")
):
    incentive = (contractAPR - buyRate) * 1000
    return JSONResponse(content={"incentive": round(incentive, 2)})

@app.get("/calculate-compensation")
def calculate_compensation(
    dealerName: str = Query(..., description="Dealer name to look up compensation")
):
    dealerName_cleaned = dealerName.strip().lower()
    print(f"Received dealer name: {dealerName_cleaned}")
    # Simulate a database lookup or API call

    compensation = dealer_data.get(dealerName_cleaned)

    if compensation is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Dealer '{dealerName}' not found"}
        )

    return {"dealerName": dealerName, "compensation": compensation}