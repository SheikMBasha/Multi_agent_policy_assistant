from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Dealer Compensation & GAP Refund API")

# Funding address info by RBC number
funding_addresses_by_rbc = {
    "RBC123": "Wells Fargo Auto, 100 Main St, Dallas, TX 75201",
    "RBC456": "Wells Fargo Auto, 200 Market St, Houston, TX 77002",
    "RBC789": "Wells Fargo Auto, 300 Sunset Blvd, Austin, TX 78701",
}

# Dealer data with compensation and GAP refund
dealer_data = {
    "lithium motors": {
        "compensation": 1500.00,
        "gap_refund": 220.00,
        "sales": {
            "January": 3500.00,
            "February": 4200.00,
            "March": 4000.00
        }
    },
    "sonic automotive": {
        "compensation": 1750.50,
        "gap_refund": 245.50,
        "sales": {
            "January": 4800.00,
            "February": 5000.00,
            "March": 4700.00
        }
    },
    "groupon automotive": {
        "compensation": 1325.75,
        "gap_refund": 180.75,
        "sales": {
            "January": 3100.00,
            "February": 2900.00,
            "March": 3300.00
        }
    },
    "prestige motors": {
        "compensation": 1005.51,
        "gap_refund": 210.00,
        "sales": {
            "January": 2700.00,
            "February": 2500.00,
            "March": 3000.00
        }
    }
}

# Calculate incentive from APR and Buy Rate
@app.get("/calculate-incentive")
def calculate_incentive(
    contractAPR: float = Query(..., description="Contract APR"),
    buyRate: float = Query(..., description="Buy Rate")
):
    incentive = (contractAPR - buyRate) * 1000
    return JSONResponse(content={"incentive": round(incentive, 2)})

# Get dealer compensation
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

    return {"dealerName": dealerName, "compensation": dealer_info["compensation"]}

# Get GAP refund amount
@app.get("/get-gap-refund")
def get_gap_refund(
    dealerName: str = Query(..., description="Dealer name to look up GAP refund")
):
    dealerName_cleaned = dealerName.strip().lower()
    print(f"Received dealer name for GAP refund: {dealerName_cleaned}")

    dealer_info = dealer_data.get(dealerName_cleaned)

    if dealer_info is None or "gap_refund" not in dealer_info:
        return JSONResponse(
            status_code=404,
            content={"error": f"GAP refund not found for dealer '{dealerName}'"}
        )

    return {
        "dealerName": dealerName,
        "gapRefund": dealer_info["gap_refund"]
    }

# Get funding address using RBC number
@app.get("/get-funding-address")
def get_funding_address(
    rbcNumber: str = Query(..., description="RBC Number of the dealership")
):
    rbc_cleaned = rbcNumber.strip().upper()
    print(f"Received RBC number: {rbc_cleaned}")

    address = funding_addresses_by_rbc.get(rbc_cleaned)

    if address is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"No funding address found for RBC number '{rbcNumber}'"}
        )

    return {
        "rbcNumber": rbcNumber,
        "fundingAddress": address
    }
