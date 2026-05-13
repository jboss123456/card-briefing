import os
import time
import requests
from twilio.rest import Client
from datetime import datetime, timedelta

# ─── TWILIO CONFIG ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN")
SANDBOX_FROM  = "whatsapp:+14155238886"
MY_WHATSAPP   = "whatsapp:+15148339119"

# ─── TCG API CONFIG ──────────────────────────────────────────────────────────────────────────────────────────────────────────
TCG_API_KEY  = os.environ.get("TCG_API_KEY")
TCG_BASE_URL = "https://api.tcgapi.dev"
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# ─── MY CARDS ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
MY_CARDS = {
    "Luffy OP13-118 CGC Pristine 10": {"name": "Luffy", "number": "OP13-118", "game": "one-piece-card-game"},
    "Deoxys VSTAR GG46 CGC Pristine 10": {"name": "Deoxys VSTAR", "number": "GG46", "game": "pokemon"},
}

# ─── ONE PIECE WATCHLIST ──────────────────────────────────────────────────────────────────────────────────────────
ONE_PIECE_WATCHLIST = {
    "Zoro OP13-119 CGC 10": {"name": "Zoro", "number": "OP13-119", "game": "one-piece-card-game"},
    "Sanji OP13-117 CGC 10": {"name": "Sanji", "number": "OP13-117", "game": "one-piece-card-game"},
    "Nami OP13-116 CGC 10": {"name": "Nami", "number": "OP13-116", "game": "one-piece-card-game"},
    "Gol D Roger OP13-118 CGC 10": {"name": "Roger", "number": "OP13-118", "game": "one-piece-card-game"},
}

# ─── POKEMON WATCHLIST ──────────────────────────────────────────────────────────────────────────────────────────────────────────
POKEMON_WATCHLIST = {
    "Charizard ex 199 PSA 10": {"name": "Charizard ex", "number": "199", "game": "pokemon"},
    "Umbreon VMAX Alt Art PSA 10": {"name": "Umbreon VMAX", "number": "215", "game": "pokemon"},
    "Pikachu VMAX Rainbow PSA 10": {"name": "Pikachu VMAX", "number": "188", "game": "pokemon"},
    "Rayquaza VMAX Alt Art PSA 10": {"name": "Rayquaza VMAX", "number": "218", "game": "pokemon"},
    "API TEST": {"name": "Pikachu", "number": "1", "game": "pokemon"},
}
# ─── TCG API FUNCTIONS ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def get_card_price(card_info):
    try:
        headers = {"x-api-key": TCG_API_KEY}
        params = {
            "q": card_info["name"],
            "game": card_info["game"],
        }
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

def get_one_piece_price(card_info):
    try:
        card_number = card_info.get('number', '')
        resp = requests.get(f'https://optcgapi.com/api/sets/card/{card_number}/', timeout=10)
        print(f'OP API [{card_info["name"]}]: {resp.status_code} {resp.text[:300]}')
        data = resp.json()
        price = data.get('price') or data.get('market_price') or data.get('tcgplayer_price') or data.get('low_price')
        change = data.get('price_change') or data.get('change_7d')
        return price, change
    except Exception as e:
        print(f'OP API error [{card_info["name"]}]: {e}')
        return None, None

def calc_pct(change_7d):
    return change_7d if change_7d is not None else None
# ─── SECTION BUILDERS ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def build_my_cards_section():
    lines = ["━━━━━━━━━━━━━━━", "U0001f48e MY CARDS", "━━━━━━━━━━━━━━━"]
    for name, info in MY_CARDS.items():
        price, change = get_one_piece_price(info) if info.get('game') == 'one-piece-card-game' else get_card_price(info)
        lines.append(f"\n{name}")
        if not price:
            lines.append(" No price data found")
            continue
        lines.append(f" Market: ${price:.2f}")
        if change is not None:
            arrow = "▲" if change >= 0 else "▼"
            lines.append(f" 7d change: {arrow} {abs(change):.1f}%")
        time.sleep(0.5)
    return "\n".join(lines)

def build_watchlist_section(title, emoji, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} {title}", "━━━━━━━━━━━━━━━"]
    for name, info in watchlist.items():
        price, change = get_one_piece_price(info) if info.get('game') == 'one-piece-card-game' else get_card_price(info)
        flag = ""
        if change is not None:
            if change >= 15:
                flag = " U0001f680"
            elif change <= -15:
                flag = " ⚠️"
        lines.append(f"\n{name}{flag}")
        if not price:
            lines.append(" No price data found")
            continue
        lines.append(f" Market: ${price:.2f}")
        if change is not None:
            arrow = "▲" if change >= 0 else "▼"
            lines.append(f" 7d change: {arrow} {abs(change):.1f}%")
        time.sleep(0.5)
    return "\n".join(lines)

def build_hype_radar_section(title, emoji, subreddit, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} HYPE RADAR — {title}", "━━━━━━━━━━━━━━━"]
    reddit_mentions = {}
    try:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        posts = r.json().get("data", {}).get("children", [])
        cutoff = datetime.utcnow() - timedelta(hours=24)
        for post in posts:
            data = post.get("data", {})
            created = datetime.utcfromtimestamp(data.get("created_utc", 0))
            if created < cutoff:
                continue
            text = (data.get("title", "") + " " + data.get("selftext", "")).lower()
            for card_name in watchlist:
                short = watchlist[card_name]["name"].lower()
                if short in text:
                    reddit_mentions[card_name] = reddit_mentions.get(card_name, 0) + 1
    except Exception as e:
        print(f"Reddit error: {e}")
    for name, info in watchlist.items():
        mentions = reddit_mentions.get(name, 0)
        buzz = f" U0001f525x{mentions}" if mentions > 0 else ""
        lines.append(f"\n{name}{buzz}")
    return "\n".join(lines)

def build_message():
    today = datetime.utcnow().strftime("%a %b %-d")
    header = f"U0001f4c8 CARD BRIEFING — {today}"
    my_cards = build_my_cards_section()
    op_watch = build_watchlist_section("ONE PIECE WATCHLIST", "U0001f3f4", ONE_PIECE_WATCHLIST)
    pk_watch = build_watchlist_section("POKEMON WATCHLIST", "U0001f004", POKEMON_WATCHLIST)
    op_hype = build_hype_radar_section("ONE PIECE", "U0001f50d", "OnePieceCardGame", ONE_PIECE_WATCHLIST)
    pk_hype = build_hype_radar_section("POKEMON", "U0001f50d", "pokemontcg", POKEMON_WATCHLIST)
    return "\n\n".join([header, my_cards, op_watch, pk_watch, op_hype, pk_hype])

def send_whatsapp(message):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.messages.create(
        from_=SANDBOX_FROM,
        to=MY_WHATSAPP,
        body=message
    )

if __name__ == "__main__":
    print("Building message...")
    msg = build_message()
    print(msg)
    send_whatsapp(msg)
    print("Sent!")
