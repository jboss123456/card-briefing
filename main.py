import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
from datetime import datetime, timedelta

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
SANDBOX_FROM = "whatsapp:+14155238886"
MY_WHATSAPP = "whatsapp:+15148339119"

TCG_API_KEY = os.environ.get("TCG_API_KEY")
TCG_BASE_URL = "https://api.tcgapi.dev"
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")
PRICE_HISTORY_FILE = "price_history.json"

MY_CARDS = {
        "Luffy OP13-118 CGC Pristine 10": {"name": "Luffy OP13-118 CGC 10", "number": "OP13-118", "game": "one-piece-card-game"},
        "Deoxys VSTAR GG46 CGC Pristine 10": {"name": "Deoxys VSTAR", "number": "GG46", "game": "pokemon"},
}

ONE_PIECE_WATCHLIST = {
        "Zoro OP13-119 CGC 10": {"name": "Zoro OP13-119 CGC 10", "number": "OP13-119", "game": "one-piece-card-game"},
        "Sanji OP13-117 CGC 10": {"name": "Sanji OP13-117 CGC 10", "number": "OP13-117", "game": "one-piece-card-game"},
        "Nami OP13-116 CGC 10": {"name": "Nami OP13-116 CGC 10", "number": "OP13-116", "game": "one-piece-card-game"},
        "Gol D Roger OP13-118 CGC 10": {"name": "Roger OP13-118 CGC 10", "number": "OP13-118", "game": "one-piece-card-game"},
}

POKEMON_WATCHLIST = {
        "Charizard ex 199 PSA 10": {"name": "Charizard ex", "number": "199", "game": "pokemon"},
        "Umbreon VMAX Alt Art PSA 10": {"name": "Umbreon VMAX", "number": "215", "game": "pokemon"},
        "Pikachu VMAX Rainbow PSA 10": {"name": "Pikachu VMAX", "number": "188", "game": "pokemon"},
        "Rayquaza VMAX Alt Art PSA 10": {"name": "Rayquaza VMAX", "number": "218", "game": "pokemon"},
        "API TEST": {"name": "Pikachu", "number": "1", "game": "pokemon"},
}

def load_price_history():
        if os.path.exists(PRICE_HISTORY_FILE):
                    try:
                                    with open(PRICE_HISTORY_FILE, "r") as f:
                                                        return json.load(f)
                    except Exception:
                                    pass
                            return {}

    def save_price_history(history):
            try:
                        with open(PRICE_HISTORY_FILE, "w") as f:
                                        json.dump(history, f, indent=2)
            except Exception as e:
                        print(f"Could not save price history: {e}")

        _price_history = None

def get_history():
        global _price_history
        if _price_history is None:
                    _price_history = load_price_history()
                return _price_history

def get_ebay_graded_price(card_info):
        """Scrape eBay completed listings for a graded card and return avg of last 5 sold prices."""
    card_name = card_info.get("name", "")
    card_key = card_info.get("number", card_name)
    try:
                query = card_name.replace(" ", "+")
                ebay_url = (
                    "https://www.ebay.com/sch/i.html"
                    "?_nkw=" + query +
                    "&LH_Sold=1&LH_Complete=1&LH_ItemCondition=3000&_sop=13"
                )
                params = {
                    "api_key": SCRAPER_API_KEY,
                    "url": ebay_url,
                    "render": "false",
                }
                print(f"eBay scrape [{card_name}]: fetching eBay sold listings...")
                resp = requests.get("http://api.scraperapi.com/", params=params, timeout=30)
                print(f"eBay scrape [{card_name}]: status={resp.status_code} len={len(resp.text)}")
                if resp.status_code != 200:
                                raise ValueError(f"ScraperAPI returned {resp.status_code}")
                            html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        price_elements = (
                        soup.select(".s-item__price") or
                        soup.select("[class*=price]") or
                        soup.select(".item__price") or
                        []
        )
        prices = []
        for tag in price_elements:
                        text = tag.get_text(strip=True)
                        text = text.split(" to ")[0]
                        m = re.search(r"[\$]([\d,]+\.\d{2})", text)
                        if m:
                                            val = float(m.group(1).replace(",", ""))
                                            if 10 < val < 5000 and val != 20.00:
                                                                    prices.append(val)
                                                        if not prices:
                                                                        raw_prices = re.findall(r'"soldPrice"\s*:\s*\{[^}]*"value"\s*:\s*"([\d.]+)"', html)
                                                                        if not raw_prices:
                                                                                            raw_prices = re.findall(r'"price"\s*:\s*"([\d.]+)"', html)
                                                                                        if not raw_prices:
                                                                                                            raw_prices = re.findall(r'US\s*\$([\d,]+\.\d{2})', html)
                                                                                                        for p in raw_prices[:20]:
                                                                                                                            try:
                                                                                                                                                    val = float(str(p).replace(",", ""))
                                                                                                                                                    if 10 < val < 5000 and val != 20.00:
                                                                                                                                                                                prices.append(val)
                                                                                                                                except Exception:
                                                                                                                                pass
                                                                                                                    print(f"eBay scrape [{card_name}]: raw prices extracted before averaging: {prices[:10]}")
                                                                    print(f"eBay scrape [{card_name}]: found {len(prices)} prices: {prices[:10]}")
                                    if not prices:
                                                    raise ValueError("No sold prices found on eBay")
                                                recent = prices[:5]
        avg_price = round(sum(recent) / len(recent), 2)
        print(f"eBay scrape [{card_name}]: avg of {len(recent)} prices = ${avg_price}")
        history = get_history()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        card_history = history.get(card_key, {})
        card_history[today_str] = avg_price
        cutoff = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d")
        card_history = {k: v for k, v in card_history.items() if k >= cutoff}
        history[card_key] = card_history
        past_price = None
        for days_back in range(7, 14):
                        check_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            if check_date in card_history:
                                past_price = card_history[check_date]
                                break
                        pct_change = None
        if past_price and past_price > 0:
                        pct_change = round(((avg_price - past_price) / past_price) * 100, 1)
        return avg_price, pct_change
except Exception as e:
        print(f"eBay scrape error [{card_name}]: {e}")
        history = get_history()
        card_history = history.get(card_key, {})
        if card_history:
                        last_date = max(card_history.keys())
            last_price = card_history[last_date]
            print(f"eBay scrape [{card_name}]: using last known price ${last_price} from {last_date}")
            return last_price, None
        return None, None


def get_card_price(card_info):
        try:
                    headers = {"x-api-key": TCG_API_KEY}
                    params = {"q": card_info["name"], "game": card_info["game"]}
                    resp = requests.get(f"{TCG_BASE_URL}/v1/search", headers=headers, params=params, timeout=10)
                    print(f"TCG API [{card_info['name']}]: {resp.status_code} {resp.text[:300]}")
                    data = resp.json()
                    cards = data.get("data", []) or data.get("results", [])
                    if not cards:
                                    return None, None
                                target_number = card_info.get("number", "")
                    card = None
                    if target_number:
                                    for c in cards:
                                                        if target_number.lower() in (c.get("number") or "").lower():
                                                                                card = c
                                                                                break
                                                                    if card is None:
                                                                                    card = cards[0]
                                                                                print(f"TCG API MATCH [{card_info['name']}]: matched '{card.get('name')}' #{card.get('number')} market={card.get('market_price')}")
                                                prices = card.get("prices", {})
                                market = (prices.get("market_price") or prices.get("market") or
                              prices.get("mid") or prices.get("low") or prices.get("high"))
                    if market is None:
                                    market = card.get("market_price") or card.get("low_price")
                                change_7d = card.get("price_change_7d") or card.get("priceChange7d")
                    return market, change_7d
except Exception as e:
            print(f"TCG API error [{card_info['name']}]: {e}")
            return None, None

    def format_change(change):
            if change is None:
                        return "n/a"
                    if change > 0:
                                return f"+{change:.1f}%"
elif change < 0:
        return f"{change:.1f}%"
else:
        return "0%"

def build_my_cards_section():
        out = ["MY CARDS"]
    for label, info in MY_CARDS.items():
                if info.get('game') == 'one-piece-card-game':
                                price, change = get_ebay_graded_price(info)
else:
            price, change = get_card_price(info)
        out.append(f"\n{label}")
        if price is None:
                        out.append("  No price data found")
                        continue
                    out.append(f"  Market: ${price:.2f}")
        out.append(f"  7d change: {format_change(change)}")
        time.sleep(0.5)
    return "\n".join(out)

def build_watchlist_section(title, emoji, watchlist):
        out = [f"\n{emoji} {title}"]
    for label, info in watchlist.items():
                if info.get('game') == 'one-piece-card-game':
                                price, change = get_ebay_graded_price(info)
else:
            price, change = get_card_price(info)
        flag = ""
        if change is not None:
                        if change >= 15:
                                            flag = " (HOT)"
        elif change <= -15:
                flag = " (WARN)"
        out.append(f"\n{label}{flag}")
        if price is None:
                        out.append("  No price data found")
                        continue
                    out.append(f"  Market: ${price:.2f}")
        out.append(f"  7d change: {format_change(change)}")
        time.sleep(0.5)
    return "\n".join(out)

def build_hype_radar_section(title, emoji, game, watchlist):
        out = [f"\n{emoji} {title} HYPE RADAR"]
    hype_cards = []
    for label, info in watchlist.items():
                if info.get("game") != game:
                                continue
                            if info.get('game') == 'one-piece-card-game':
                                            price, change = get_ebay_graded_price(info)
else:
            price, change = get_card_price(info)
        if change is not None and abs(change) >= 10:
                        hype_cards.append((label, price, change))
                    time.sleep(0.5)
    if not hype_cards:
                out.append("  No big movers today")
else:
        hype_cards.sort(key=lambda x: abs(x[2]), reverse=True)
        for label, price, change in hype_cards:
                        price_str = f"${price:.2f}" if price else "N/A"
                        out.append(f"  {label}: {price_str} {format_change(change)}")
                return "\n".join(out)

def build_message():
        now = datetime.utcnow() - timedelta(hours=4)
    date_str = now.strftime("%A, %B %-d")
    header = f"DAILY CARD BRIEFING\n{date_str}"
    my_cards = build_my_cards_section()
    op_watch = build_watchlist_section("ONE PIECE WATCHLIST", "OP", ONE_PIECE_WATCHLIST)
    pk_watch = build_watchlist_section("POKEMON WATCHLIST", "PK", POKEMON_WATCHLIST)
    op_hype = build_hype_radar_section("ONE PIECE", "OP", "one-piece-card-game", ONE_PIECE_WATCHLIST)
    pk_hype = build_hype_radar_section("POKEMON", "PK", "pokemontcg", POKEMON_WATCHLIST)
    if _price_history:
                save_price_history(_price_history)
    return "\n\n".join([header, my_cards, op_watch, pk_watch, op_hype, pk_hype])

def send_whatsapp(message):
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.messages.create(from_=SANDBOX_FROM, to=MY_WHATSAPP, body=message)

if __name__ == "__main__":
        print("Building message...")
    msg = build_message()
    print(msg)
    send_whatsapp(msg)
    print("Sent!")
