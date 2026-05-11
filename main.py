import os
import time
import requests
from twilio.rest import Client
from datetime import datetime, timedelta
SCRAPER_KEY = os.environ.get('SCRAPER_API_KEY')

# ─── TWILIO CONFIG ────────────────────────────────────────────────────────────────────────────────────
ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN")
SANDBOX_FROM = "whatsapp:+14155238886"
MY_WHATSAPP  = "whatsapp:+15148339119"

# ─── MY CARDS ─────────────────────────────────────────────────────────────────────────────────────────
MY_CARDS = {
    "Luffy OP13-118 CGC Pristine 10": "One Piece Luffy OP13-118 CGC Pristine 10",
    "Deoxys VSTAR GG46 CGC Pristine 10": "Deoxys VSTAR GG46 CGC Pristine 10",
}

# ─── ONE PIECE WATCHLIST ────────────────────────────────────────────────────────────────────────────
ONE_PIECE_WATCHLIST = {
    "Zoro OP13-119 CGC 10": "Zoro OP13-119 CGC 10",
    "Sanji OP13-117 CGC 10": "Sanji OP13-117 CGC 10",
    "Nami OP13-116 CGC 10": "Nami OP13-116 CGC 10",
    "Gol D Roger OP13-118 CGC 10": "Gol D Roger OP13-118 CGC 10",
}

# ─── POKEMON WATCHLIST ────────────────────────────────────────────────────────────────────────────────────
POKEMON_WATCHLIST = {
    "Charizard ex 199 PSA 10": "Charizard ex 199 PSA 10",
    "Umbreon VMAX Alt Art PSA 10": "Umbreon VMAX Alt Art PSA 10",
    "Pikachu VMAX Rainbow PSA 10": "Pikachu VMAX Rainbow PSA 10",
    "Rayquaza VMAX Alt Art PSA 10": "Rayquaza VMAX Alt Art PSA 10",
    "API TEST": "Pikachu PSA 10",
}

# ─── PRICECHARTING API ────────────────────────────────────────────────────────────────────────────────────
def get_pricecharting_price(query):
    try:
        url = "https://www.pricecharting.com/api/products"
        params = {"q": query, "status": "price"}
        resp = requests.get(url, params=params, timeout=10)
        print(f"PriceCharting [{query}]: {resp.status_code} {resp.text[:300]}")
        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None
        product = products[0]
        # graded prices in cents
        psa10 = product.get("graded-price-10")
        cib   = product.get("cib-price")
        price = psa10 or cib
        if price:
            return round(float(price) / 100, 2)
        return None
    except Exception as e:
        print(f"PriceCharting error: {e}")
        return None

def get_pricecharting_history(query):
    try:
        url = "https://www.pricecharting.com/api/products"
        params = {"q": query, "status": "price"}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None, None, None
        product = products[0]
        psa10       = product.get("graded-price-10")
        psa9        = product.get("graded-price-9")
        loose       = product.get("loose-price")
        current     = round(float(psa10) / 100, 2) if psa10 else None
        month_ago   = round(float(psa9) / 100, 2) if psa9 else None
        return current, month_ago, product.get("name", query)
    except Exception as e:
        print(f"PriceCharting history error: {e}")
        return None, None, None

def calc_pct(current, prior):
    if current and prior and prior > 0:
        return ((current - prior) / prior) * 100
    return None

# ─── SECTION BUILDERS ───────────────────────────────────────────────────────────────────────────────────────
def build_my_cards_section():
    lines = ["━━━━━━━━━━━━━━━", "💎 MY CARDS", "━━━━━━━━━━━━━━━"]
    for name, query in MY_CARDS.items():
        current, prior, product_name = get_pricecharting_history(query)
        lines.append(f"\n{name}")
        if not current:
            lines.append("  No price data found")
            continue
        lines.append(f"Current: ${current:.0f}")
        pct = calc_pct(current, prior)
        if pct is not None:
            arrow = "▲" if pct >= 0 else "▼"
            lines.append(f"vs prior grade: {arrow} {abs(pct):.1f}%")
        time.sleep(0.5)
    return "\n".join(lines)

def build_watchlist_section(title, emoji, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} {title}", "━━━━━━━━━━━━━━━"]
    for name, query in watchlist.items():
        current, prior, product_name = get_pricecharting_history(query)
        pct = calc_pct(current, prior)
        flag = ""
        if pct is not None:
            if pct >= 15:
                flag = " 🚀"
            elif pct <= -15:
                flag = " ⚠️"
        lines.append(f"\n{name}{flag}")
        if not current:
            lines.append("  No price data found")
            continue
        lines.append(f"Latest: ${current:.0f}")
        if pct is not None:
            arrow = "▲" if pct >= 0 else "▼"
            lines.append(f"vs prior: {arrow} {abs(pct):.1f}%")
        time.sleep(0.5)
    return "\n".join(lines)

def build_hype_radar_section(title, emoji, subreddit, watchlist):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} HYPE RADAR — {title}", "━━━━━━━━━━━━━━━"]
    reddit_mentions = {}
    try:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
        r = requests.get(f'http://api.scraperapi.com?api_key={SCRAPER_KEY}&url=' + requests.utils.quote(url, safe=''), headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        posts = r.json().get("data", {}).get("children", [])
        cutoff = datetime.utcnow() - timedelta(hours=24)
        for post in posts:
            data = post.get("data", {})
            created = datetime.utcfromtimestamp(data.get("created_utc", 0))
            if created < cutoff:
                continue
            text = (data.get("title", "") + " " + data.get("selftext", "")).lower()
            for card_name in watchlist:
                keywords = card_name.lower().split()
                if all(kw in text for kw in keywords[:2]):
                    reddit_mentions[card_name] = reddit_mentions.get(card_name, 0) + 1
        time.sleep(1)
    except Exception as e:
        lines.append(f"Reddit fetch error: {e}")

    hype_cards = []
    for name, query in watchlist.items():
        mentions = reddit_mentions.get(name, 0)
        if mentions >= 3:
            current, prior, _ = get_pricecharting_history(query)
            pct = calc_pct(current, prior)
            if pct and pct >= 15:
                hype_cards.append((name, mentions, pct, current))

    if not hype_cards:
        lines.append("No hype signals today.")
    else:
        for name, mentions, pct, current in hype_cards:
            lines.append(f"\n{name}")
            lines.append(f"Reddit mentions (24hr): {mentions}")
            lines.append(f"Price change: +{pct:.1f}%")
            if current:
                lines.append(f"Current: ${current:.0f}")

    return "\n".join(lines)

# ─── MAIN ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def build_message():
    now_est = datetime.utcnow() - timedelta(hours=5)
    today = now_est.strftime("%a %b %-d")
    lines = [f"📈 CARD BRIEFING — {today}"]
    lines.append(build_my_cards_section())
    lines.append(build_watchlist_section("ONE PIECE WATCHLIST", "🏴‍☠️", ONE_PIECE_WATCHLIST))
    lines.append(build_watchlist_section("POKEMON WATCHLIST", "⚡", POKEMON_WATCHLIST))
    lines.append(build_hype_radar_section("ONE PIECE", "🔥", "OnePieceTCG", ONE_PIECE_WATCHLIST))
    lines.append(build_hype_radar_section("POKEMON", "🔥", "PokemonTCG", POKEMON_WATCHLIST))
    return "\n".join(lines)

def send_whatsapp(body):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    message = client.messages.create(
        body=body,
        from_=SANDBOX_FROM,
        to=MY_WHATSAPP,
    )
    print(f"Sent! SID: {message.sid}")

if __name__ == "__main__":
    print("Building message...")
    msg = build_message()
    print(msg)
    print("Sending WhatsApp message...")
    send_whatsapp(msg)
