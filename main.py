from dotenv import load_dotenv
import os
import asyncio
from cetesdirecto_scrapper import CDScrapper
from playwright.async_api import async_playwright


async def main():
    # Load environment variables from .env file
    load_dotenv()

    # Access the environment variables
    user = os.getenv("CETESDIRECTO_USR")
    pwd = os.getenv("CETESDIRECTO_PWD")
    url = os.getenv("CETESDIRECTO_URL")
    scrapper = CDScrapper(url, user, pwd)
    async with async_playwright() as p:
        await scrapper.init_browser(p)
        await scrapper.login()
        portfolio = await scrapper.fetch_portafolio()
        print(portfolio)
        await scrapper.logout()


if __name__ == "__main__":
    asyncio.run(main())
