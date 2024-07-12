import requests
from bs4 import BeautifulSoup
import asyncio

INIT_URI = "web/init"
LOGIN_URI = "SSOSVD_wls"
IPINFO = "https://ipinfo.io"


class CDScrapper:

    def __init__(self, url, usr, pwd, options=None):
        self.usr = usr
        self.pwd = pwd
        self.browser = None
        self.page = None
        self.context = None
        self.options = options
        self.url = url

    def get_geolocation(self):
        response = requests.get(IPINFO)
        data = response.json()
        loc = data["loc"].split(",")
        return float(loc[0]), float(loc[1])

    async def init_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=False)
        real_latitude, real_longitude = self.get_geolocation()
        self.context = await self.browser.new_context(
            permissions=["geolocation"],
            viewport={"width": 1280, "height": 720},
            geolocation={"latitude": real_latitude, "longitude": real_longitude},
        )
        self.page = await self.context.new_page()

    async def login(self, timeout=50000):
        await self.page.goto(
            f"{self.url}/{LOGIN_URI}", wait_until="networkidle", timeout=timeout
        )
        await self.page.fill("#userId", self.usr)
        await asyncio.sleep(1)
        await self.page.click("#continuarBtn")
        await asyncio.sleep(1)
        await self.page.wait_for_load_state("networkidle")

        await self.page.fill("#pwdId", self.pwd)
        await asyncio.sleep(1)
        await self.page.click("#accederBtn")
        await self.page.wait_for_load_state("networkidle")

    async def logout(self, timeout=50000):
        await self.page.goto(
            f"{self.url}/{INIT_URI}", wait_until="networkidle", timeout=timeout
        )
        await self.page.wait_for_selector("[data-name='cerrarSesion']")
        await self.page.click("[data-name='cerrarSesion']")
        await self.page.wait_for_load_state("networkidle")

    async def fetch_portafolio(self, timeout=50000):
        await self.page.wait_for_selector(".portafolioMenu", timeout=timeout)
        await self.page.click(".portafolioMenu")
        await asyncio.sleep(1)
        await self.page.wait_for_load_state("networkidle")

        portafolio_html = await self.page.evaluate(
            """() => {
            const element = document.querySelector('.portafolio');
            return element ? element.innerHTML : null;
        }"""
        )

        if not portafolio_html:
            print("Portafolio element not found.")
            return None

        soup = BeautifulSoup(portafolio_html, "html.parser")
        instrumentos_div = soup.find("div", class_="instrumentos")
        instrumentos = self.parse_instrumentos(instrumentos_div)
        return instrumentos

    async def parse_instrumentos(self, soup):
        instrumentos = []

        for instrumento in soup.find_all("div", class_="instrumento"):
            name = rate = montoInv = plusMinus = montoDisp = None

            nombreInstrumento = instrumento.find("div", class_="nombreInstrumento")
            if nombreInstrumento:
                tituloInstrumento = nombreInstrumento.find(
                    "div", class_="tituloInstrumento"
                )
                if tituloInstrumento:
                    txtInstrumento = tituloInstrumento.find(
                        "span", class_="txtInstrumento"
                    )
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
                txtInstrumento = montoDisptoInvDesktop.find(
                    "span", class_="txtInstrumento"
                )
                if txtInstrumento:
                    montoDisp = txtInstrumento.get_text(strip=True)

            valoresInstrumento = instrumento.find("div", class_="valoresInstrumento")
            if valoresInstrumento:
                valorInstrumento = valoresInstrumento.find(
                    "div", class_="valorInstrumento"
                )
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
