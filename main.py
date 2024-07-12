from dotenv import load_dotenv
import os
import asyncio
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup
import json

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
user = os.getenv("CETESDIRECTO_USR")
pwd = os.getenv("CETESDIRECTO_PWD")
url = os.getenv("CETESDIRECTO_URL")


def get_geolocation():
    response = requests.get("https://ipinfo.io")
    data = response.json()
    loc = data["loc"].split(",")
    return float(loc[0]), float(loc[1])


def parse_html(portafolio_html):
    soup = BeautifulSoup(portafolio_html, "html.parser")
    instrumentos_div = soup.find("div", class_="instrumentos")
    print(instrumentos_div.prettify())
    total_instrumentos_div = soup.find("div", class_="totalInstrumentos")
    print(total_instrumentos_div.prettify())
    instrumentos = parse_instrumentos(instrumentos_div)
    return instrumentos


def parse_instrumentos(soup):
    instrumentos = []

    for instrumento in soup.find_all("div", class_="instrumento"):
        name = rate = montoInv = plusMinus = montoDisp = None

        nombreInstrumento = instrumento.find("div", class_="nombreInstrumento")
        if nombreInstrumento:
            tituloInstrumento = nombreInstrumento.find(
                "div", class_="tituloInstrumento"
            )
            if tituloInstrumento:
                txtInstrumento = tituloInstrumento.find("span", class_="txtInstrumento")
                name = txtInstrumento.get_text(strip=True)
                percentInstrumento = tituloInstrumento.find(
                    "span", class_="percentInstrumento"
                )
                if percentInstrumento:
                    rate = percentInstrumento.get_text(strip=True)
        if "REMANENTES" in name:
            continue
        montoInvDesktop = instrumento.find("div", class_="montoInvDesktop")
        if montoInvDesktop:
            txtInstrumento = montoInvDesktop.find("span", class_="txtInstrumento")
            if txtInstrumento:
                montoInv = txtInstrumento.get_text(strip=True)

        plusMinusDesktop = instrumento.find("div", class_="plusMinusDesktop")
        if plusMinusDesktop:
            txtInstrumento = plusMinusDesktop.find("span", class_="txtInstrumento")
            if txtInstrumento:
                plusMinus = txtInstrumento.get_text(strip=True)

        montoDisptoInvDesktop = instrumento.find("div", class_="montoDispDesktop")
        if montoDisptoInvDesktop:
            txtInstrumento = montoDisptoInvDesktop.find("span", class_="txtInstrumento")
            if txtInstrumento:
                montoDisp = txtInstrumento.get_text(strip=True)

        valoresInstrumento = instrumento.find("div", class_="valoresInstrumento")
        if valoresInstrumento:
            valorInstrumento = valoresInstrumento.find("div", class_="valorInstrumento")
            if valorInstrumento:
                totalInstrumento = valorInstrumento.find(
                    "span", class_="totalInstrumento"
                )
                if totalInstrumento:
                    montoValuado = totalInstrumento.get_text(strip=True)

        instrumentos.append(
            {
                "name": name,
                "rate": rate,
                "montoInv": montoInv,
                "plusMinus": plusMinus,
                "montoDisp": montoDisp,
                "montoValuado": montoValuado,
            }
        )

    return instrumentos


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        real_latitude, real_longitude = get_geolocation()
        context = await browser.new_context(
            permissions=["geolocation"],
            viewport={"width": 1280, "height": 720},
            geolocation={"latitude": real_latitude, "longitude": real_longitude},
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.fill("#userId", user)
        await page.click("#continuarBtn")
        await page.wait_for_load_state("networkidle")

        await page.fill("#pwdId", pwd)
        await page.click("#accederBtn")
        await page.wait_for_load_state("networkidle")

        await page.wait_for_selector(".portafolioMenu", timeout=50000)
        await page.click(".portafolioMenu")
        await page.wait_for_load_state("networkidle")

        # Get the HTML content of the div with class "portafolio"
        portafolio_html = await page.evaluate(
            """() => {
            const element = document.querySelector('.portafolio');
            return element ? element.innerHTML : null;
        }"""
        )

        if not portafolio_html:
            print("Portafolio element not found.")
            return
        instrumentos = parse_html(portafolio_html)
        with open("data/cetes.json", "w") as json_file:
            json.dump(instrumentos, json_file, indent=4)
        await browser.close()


asyncio.run(main())
