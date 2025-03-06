import requests
import schedule
import time
import asyncio
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
from telegram.ext import Application
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import os
from dotenv import load_dotenv

# Timezone instellen op Amsterdam
amsterdam_tz = pytz.timezone('Europe/Amsterdam')

# Token en chat-ID"
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Prijsdrempels voor alerts
ALERT_LOW = 2500
ALERT_HIGH = 4000

# Maak een bot-applicatie
bot = Application.builder().token(TOKEN).build()


# ETH Prijs ophalen
def get_eth_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd,eur"
    response = requests.get(url).json()
    if "ethereum" in response:
        price_usd = response["ethereum"].get("usd", None)
        price_eur = response["ethereum"].get("eur", None)
        return price_usd, price_eur
    return None, None


# Nieuwe functie voor historische prijzen
def get_historical_prices(days=14, currency='eur'):
    url = f"https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency={currency}&days={days}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        # Converteren van timestamps naar datetime objecten in Amsterdam tijdzone
        prices = [
            (datetime.fromtimestamp(entry[0] / 1000).astimezone(amsterdam_tz),
             entry[1]) for entry in data['prices']
        ]
        return prices
    return []


def generate_price_chart(days=14):
    try:
        # Verzamel data voor afgelopen X dagen
        data = get_historical_prices(days, 'eur')

        if len(data) < 3:
            print("⚠️ Onvoldoende data voor de grafiek.")
            return False

        # Uitpakken van data
        dates, prices = zip(*data)

        # Matplotlib configuratie
        plt.figure(figsize=(14, 7), dpi=100)

        # Lijnplot met verbeterde styling
        plt.plot(
            dates,
            prices,
            color='#1E88E5',  # Material Blue
            linewidth=3,
            marker='o',
            markersize=8,
            markerfacecolor='white',
            markeredgecolor='#1E88E5',
            markeredgewidth=2,
            label='ETH/EUR')

        # Zachte kleurovergang onder de lijn
        plt.fill_between(dates,
                         prices,
                         min(prices) * 0.99,
                         color='#1E88E5',
                         alpha=0.2)

        # Labels en titels
        plt.title('Ethereum Prijsontwikkeling (14 dagen)',
                  fontsize=16,
                  fontweight='bold')
        plt.xlabel('Datum', fontsize=12)
        plt.ylabel('Prijs (€)', fontsize=12)

        # X-as datums mooi weergeven
        plt.gcf().autofmt_xdate()

        # Toevoegen van grid
        plt.grid(True, linestyle='--', linewidth=0.5, color='#E0E0E0')

        # Annoteer hoogste en laagste prijs
        max_price = max(prices)
        min_price = min(prices)
        max_index = prices.index(max_price)
        min_index = prices.index(min_price)

        plt.annotate(f'Hoogste: €{max_price:.2f}',
                     (dates[max_index], max_price),
                     xytext=(10, 10),
                     textcoords='offset points',
                     fontsize=10,
                     color='green',
                     arrowprops=dict(arrowstyle='->', color='green'))

        plt.annotate(f'Laagste: €{min_price:.2f}',
                     (dates[min_index], min_price),
                     xytext=(10, -15),
                     textcoords='offset points',
                     fontsize=10,
                     color='red',
                     arrowprops=dict(arrowstyle='->', color='red'))

        # Opslaan van de grafiek
        plt.tight_layout()
        plt.savefig('eth_chart.png', dpi=300)
        plt.close()

        print(f"✅ Grafiek succesvol opgeslagen met {len(data)} datapunten")
        return True

    except Exception as e:
        print(f"❌ Fout bij genereren grafiek: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# Alleen koersupdate sturen
async def send_price_update():
    try:
        price_usd, price_eur = get_eth_price()
        if price_usd is None or price_eur is None:
            print("⚠️ Geen geldige API-respons.")
            return

        alert_message = ""
        if price_eur < ALERT_LOW:
            alert_message = f"🚨 *ETH onder de €{ALERT_LOW}!* \n💶 *Huidige prijs:* €{price_eur}\n"
        elif price_eur > ALERT_HIGH:
            alert_message = f"🚀 *ETH boven de €{ALERT_HIGH}!* \n💶 *Huidige prijs:* €{price_eur}\n"

        message = ("🌍 *Ethereum Prijs Update*\n"
                   "━━━━━━━━━━━━━━━━━━━━━\n"
                   f"💵 *USD:* `${price_usd}` 🇺🇸\n"
                   f"💶 *EUR:* `€{price_eur}` 🇪🇺\n"
                   "━━━━━━━━━━━━━━━━━━━━━\n"
                   f"{alert_message}")

        await bot.initialize()
        await bot.bot.send_message(chat_id=CHAT_ID,
                                   text=message,
                                   parse_mode='Markdown')
        await bot.shutdown()
    except Exception as e:
        print(f"⚠️ Fout bij prijsupdate: {str(e)}")


# Volledige update met grafiek
async def send_combined_update():
    try:
        price_usd, price_eur = get_eth_price()
        if price_usd is None or price_eur is None:
            print("⚠️ Geen geldige API-respons.")
            return

        # Gebruik laatste prijs uit de historische data als referentie
        historical_prices = get_historical_prices(2)
        yesterday_price = historical_prices[0][1] if historical_prices else None
        today_price = price_eur

        alert_message = ""
        if price_eur < ALERT_LOW:
            alert_message = f"🚨 *ETH onder de €{ALERT_LOW}!* \n💶 *Huidige prijs:* €{price_eur}\n"
        elif price_eur > ALERT_HIGH:
            alert_message = f"🚀 *ETH boven de €{ALERT_HIGH}!* \n💶 *Huidige prijs:* €{price_eur}\n"

        message = (
            "🌍 *Dagelijkse Ethereum Prijs Update *\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *USD:* `${price_usd}` 🇺🇸\n"
            f"💶 *EUR:* `€{price_eur}` 🇪🇺\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 *Dagelijkse ETH Update*\n"
            f"📅 *Date & Time:* `{datetime.now(amsterdam_tz).strftime('%d-%m-%Y %H:%M')}            `\n"
            f"📉 *Gisteren:* `€{yesterday_price if yesterday_price else 'Onbekend'}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"{alert_message}")

        print("📊 Grafiek genereren...")
        chart_created = generate_price_chart()

        print("🤖 Telegram bot initialiseren...")
        await bot.initialize()

        print("📨 Bericht versturen...")
        await bot.bot.send_message(chat_id=CHAT_ID,
                                   text=message,
                                   parse_mode='Markdown')

        if chart_created:
            try:
                print("🖼️ Grafiek verzenden...")
                with open('eth_chart.png', 'rb') as photo:
                    await bot.bot.send_photo(chat_id=CHAT_ID, photo=photo)
                print("✅ Grafiek succesvol verzonden!")
            except Exception as e:
                print(f"❌ Fout bij verzenden grafiek: {str(e)}")
                await bot.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"⚠️ Fout bij verzenden grafiek: {str(e)}",
                    parse_mode='Markdown')
        else:
            print("⚠️ Grafiek kon niet worden gegenereerd")
            await bot.bot.send_message(
                chat_id=CHAT_ID,
                text=
                "⚠️ Kon geen prijsgrafiek genereren door ontbrekende data.",
                parse_mode='Markdown')

        await bot.shutdown()
    except Exception as e:
        print(f"⚠️ Fout tijdens update: {str(e)}")


async def main():
    # Stuur eerste update bij start met grafiek
    print("📊 Bot gestart - initiële update met grafiek versturen...")
    await send_combined_update()

    # ✅ Start schedulers
    while True:
        # Gebruik Amsterdam tijdzone
        now = datetime.now(amsterdam_tz)
        print(f"⏰ Huidige tijd (Amsterdam): {now.hour}:{now.minute}")

        # Elke dag om 16:00 volledige update (Amsterdam tijd)
        if now.hour == 16 and now.minute == 0:
            print("🔔 Het is 16:00 (Amsterdam) - volledige update versturen...")
            await send_combined_update()

        # Elke minuut prijs update
        print("💰 5 Minuten-update versturen...")
        await send_price_update()

        # Wacht 300 seconden
        print("⏳ 300 seconden wachten...")
        await asyncio.sleep(900)


# 🚀 **Start de bot**
if __name__ == "__main__":
    asyncio.run(main())
