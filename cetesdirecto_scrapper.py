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
        await asyncio.sleep(1)

    async def login(self, timeout=50000):
        await self.page.goto(
            f"{self.url}/{LOGIN_URI}", wait_until="networkidle", timeout=timeout
        )
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)
        await self.page.fill("#userId", self.usr)
        await self.page.click("#continuarBtn")
        await asyncio.sleep(1)
        await self.page.wait_for_load_state("networkidle")

        await self.page.fill("#pwdId", self.pwd)
        await self.page.click("#accederBtn")
        await asyncio.sleep(5)
        await self.page.wait_for_load_state("networkidle")
        await self.page.wait_for_selector("[data-name='portafolioMenu']")

    async def logout(self, timeout=50000):
        await self.page.goto(
            f"{self.url}/{INIT_URI}", wait_until="networkidle", timeout=timeout
        )
        await self.page.wait_for_selector("[data-name='portafolioMenu']")
        await self.page.click("[data-name='cerrarSesion']")
        await self.page.wait_for_load_state("networkidle")

    async def fetch_portafolio(self, timeout=50000):
        await self.page.wait_for_selector("#portafolioMenu", timeout=timeout)
        await self.page.click("#portafolioMenu")
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
        instrumentos = await self.parse_instrumentos(soup)
        total = await self.parse_total_instrumentos(soup)
        instrumentos.append(total)
        return instrumentos

    async def parse_total_instrumentos(self, soup):
        cols = []
        totalInstrumentos = soup.find("div", class_="totalInstrumentos")
        if totalInstrumentos:
            percentInstrumento = totalInstrumentos.find(
                "span", class_="percentInstrumento"
            )
            if percentInstrumento:
                tasa = percentInstrumento.get_test(strip=True)
            for column in totalInstrumentos.find_all(
                "div", class_="totalInstrumentosSpaceDesk"
            ):
                text = column.get_text(strip=True)
                cols.append(text)
        totalInstrumentosNumeros = totalInstrumentos.find(
            "div", class_="totalInstrumentosNumeros"
        )
        if totalInstrumentosNumeros:
            txtInstrumento = totalInstrumentosNumeros.find(
                "span", class_="txtInstrumento"
            )
            if txtInstrumento:
                montoValuado = txtInstrumento.get_text(strip=True)
        return {
            "instrumento": "total",
            "tasa": tasa,
            "montoInv": cols[0],
            "plusMinus": cols[1],
            "montoDisp": cols[2],
            "montoValuado": montoValuado,
        }

    async def parse_instrumentos(self, soup):
        instrumentos = soup.find("div", class_="instrumentos")
        rows = []

        for instrumento in instrumentos.find_all("div", class_="instrumento"):
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

            rows.append(
                {
                    "instrumento": name,
                    "tasa": rate,
                    "montoInv": montoInv,
                    "plusMinus": plusMinus,
                    "montoDisp": montoDisp,
                    "montoValuado": montoValuado,
                }
            )
        return rows
