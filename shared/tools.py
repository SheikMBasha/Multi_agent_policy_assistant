import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_incentive(apr: float, buy_rate: float) -> float:
    return (apr - buy_rate) * 1000

def log_complaint(text: str):
    logger.info(f"Complaint logged: {text}")