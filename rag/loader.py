import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
import os

def load_policy_documents():
    urls = [
        "https://www.wellsfargo.com/auto-loans/vehicle-financing-101/",
        "https://www.wellsfargo.com/help/loans/auto-loans-faqs/"
    ]

    texts = []

    for url in urls:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        texts.append(text)

    pdf_url = "https://www08.wellsfargomedia.com/assets/pdf/commercial/industry/auto-dealerships/franchise-packet.pdf"
    pdf_path = "franchise-packet.pdf"

    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as f:
            f.write(requests.get(pdf_url).content)

    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        pdf_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        texts.append(pdf_text)

    return texts