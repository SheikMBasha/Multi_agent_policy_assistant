from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/calculate-incentive")
def calculate_incentive(
    contractAPR: float = Query(..., description="Contract APR"),
    buyRate: float = Query(..., description="Buy Rate")
):
    incentive = (contractAPR - buyRate) * 1000
    return JSONResponse(content={"incentive": round(incentive, 2)})
