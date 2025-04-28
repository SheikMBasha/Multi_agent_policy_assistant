from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()


dealer_data = {
    "lithium motors": {
        "compensation": 1500.00,
        "sales": {
            "January": 3500.00,
            "February": 4200.00,
            "March": 4000.00
        }
    },
    "sonic automotive": {
        "compensation": 1750.50,
        "sales": {
            "January": 4800.00,
            "February": 5000.00,
            "March": 4700.00
        }
    },
    "groupon automotive": {
        "compensation": 1325.75,
        "sales": {
            "January": 3100.00,
            "February": 2900.00,
            "March": 3300.00
        }
    },
    "prestige motors": {
        "compensation": 1005.51,
        "sales": {
            "January": 2700.00,
            "February": 2500.00,
            "March": 3000.00
        }
    }
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

    dealer_info = dealer_data.get(dealerName_cleaned)

    if dealer_info is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Dealer '{dealerName}' not found"}
        )

    compensation = dealer_info["compensation"]

    return {"dealerName": dealerName, "compensation": compensation}