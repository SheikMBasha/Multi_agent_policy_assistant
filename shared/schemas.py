from pydantic import BaseModel, Field
from typing import Optional

class DealerIncentiveRequest(BaseModel):
    contractAPR: float = Field(..., description="The APR from the customer's contract")
    buyRate: float = Field(..., description="The base rate provided to the dealer")
