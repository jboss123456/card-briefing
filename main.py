import os
import re
import time
import base64
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
from datetime import datetime, timedelta

# ─── TWILIO CONFIG ────────────────────────────────────────────────────────────
ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN")
SANDBOX_FROM = "whatsapp:+14155238886"
MY_WHATSAPP  = "whatsapp:+15148339119"

# ─── EBAY CONFIG ──────────────────────────────────────────────────────────────
EBAY_APP_ID  = os.environ.get("EBAY_APP_ID")
EBAY_CERT_ID = os.environ.get("EBAY_CERT_ID")

# ─── MY CARDS ─────────────────────────────────────────────────────────────────
MY_CARDS = {
    "Luffy OP13-118 CGC Pristine 10":    "luffy op13-118 CGC pristine 10",
    "Deoxys VSTAR GG46 CGC Pristine 10": "deoxys vstar GG46 CGC pristine 10",
}

# ─── ONE PIECE WATCHLIST ──────────────────────────────────────────────────────
ONE_PIECE_WATCHLIST = {
    "Zoro OP13-119 CGC 10":        "zoro op13-119 CGC 10",
    "Sanji OP13-117 CGC 10":       "sanji op13-117 CGC 10",
    "Nami OP13-116 CGC 10":        "nami op13-116 CGC 10",
    "Gol D Roger OP13-118 CGC 10": "gol d roger op13-118 CGC 10",
}

# ─── POKEMON WATCHLIST ────────────────────────────────────────────────────────
POKEMON_WATCHLIST = {
    "Charizard ex 199 PSA 10":      "charizard ex 199 PSA 10",
    "Umbreon VMAX Alt Art PSA 10":  "umbreon vmax alt art PSA 10",
    "Pikachu VMAX Rainbow PSA 10":  "pikachu vmax rainbow PSA 10",
    "Rayquaza VMAX Alt Art PSA 10": "rayquaza vmax alt art PSA 10",
}

# ─── EBAY API ─────────────────────────────────────────────────────────────────

def get_ebay_token():
    credentials = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"
    )
    return resp.json().get("access_token")


def get_sold_listings(query, token, days=30):
        time.sleep(2)
    resp = requests.get(
        "https://svcs.ebay.com/services/search/FindingService/v1",
        headers={
            "X-EBAY-SOA-OPERATION-NAME": "findCompletedItems",
            "X-EBAY-SOA-SERVICE-VERSION": "1.0.0",
            "X-EBAY-SOA-GLOBAL-ID": "EBAY-US",
            "X-EBAY-SOA-SECURITY-APPNAME": os.environ.get("EBAY_APP_ID", ""),
            "X-EBAY-SOA-RESPONSE-DATA-FORMAT": "JSON"
        },
        params={
            "keywords": query,
            "itemFilter(0).name": "SoldItemsOnly",
            "itemFilter(0).value": "true",
            "itemFilter(1).name": "DaysNumberOfDays",
            "itemFilter(1).value": str(days),
            "sortOrder": "EndTimeSoonest",
            "paginationInput.entriesPerPage": "10"
        }
    )
    print(resp.status_code, resp.text[:500])
    try:
        search_result = resp.json().get("findCompletedItemsResponse", [{}])[0]
        items = search_result.get("searchResult", [{}])[0].get("item", [])
    except (ValueError, IndexError, KeyError):
        return []
    results = []
    for item in items:
        try:
            amount = float(item["sellingStatus"][0]["currentPrice"][0]["__value__"])
            date = item.get("listingInfo", [{}])[0].get("endTime", ["N/A"])[0]
            date_fmt = date[:10] if date != "N/A" else "N/A"
            results.append((amount, date_fmt, f"${amount:.0f}"))
        except (KeyError, IndexError, ValueError):
            continue
    time.sleep(2)
    return results
def calc_avg(sales):
    if not sales:
        return None
    return sum(p for p, d, ps in sales) / len(sales)


# ─── SECTION BUILDERS ─────────────────────────────────────────────────────────

def build_my_cards_section(token):
    lines = ["━━━━━━━━━━━━━━━", "💎 MY CARDS", "━━━━━━━━━━━━━━━"]
    for name, query in MY_CARDS.items():
        recent = get_sold_listings(query, token, 30)
        prior  = get_sold_listings(query, token, 60)
        prior  = [s for s in prior if s not in recent]
        lines.append(f"\n{name}")
        if not recent:
            lines.append("  No recent sales found")
            continue
        avg_recent = calc_avg(recent)
        avg_prior  = calc_avg(prior)
        if avg_recent:
            lines.append(f"30-day avg: ${avg_recent:.0f}")
        if avg_recent and avg_prior and avg_prior > 0:
            pct = ((avg_recent - avg_prior) / avg_prior) * 100
            arrow = "▲" if pct >= 0 else "▼"
            lines.append(f"vs prior:   {arrow} {abs(pct):.1f}%")
        for price_val, date_str, price_str in recent[:5]:
            lines.append(f"  • {price_str} — {date_str}")
        if len(recent) < 3:
            lines.append(f"  ⚠ Low volume — {len(recent)} sale(s) found")
    return "\n".join(lines)


def build_watchlist_section(title, emoji, watchlist, token):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} {title}", "━━━━━━━━━━━━━━━"]
    for name, query in watchlist.items():
        recent = get_sold_listings(query, token, 30)
        prior  = get_sold_listings(query, token, 60)
        prior  = [s for s in prior if s not in recent]
        avg_recent = calc_avg(recent)
        avg_prior  = calc_avg(prior)
        pct = None
        if avg_recent and avg_prior and avg_prior > 0:
            pct = ((avg_recent - avg_prior) / avg_prior) * 100
        flag = ""
        if pct is not None:
            if pct >= 15:
                flag = " 🚀"
            elif pct <= -15:
                flag = " ⚠️"
        lines.append(f"\n{name}{flag}")
        if not recent:
            lines.append("  No recent sales found")
            continue
        latest_price, latest_date, latest_str = recent[0]
        lines.append(f"Latest: {latest_str} — {latest_date}")
        if avg_recent:
            if pct is not None:
                arrow = "▲" if pct >= 0 else "▼"
                lines.append(f"30-day avg: ${avg_recent:.0f} | {arrow} {abs(pct):.1f}%")
            else:
                lines.append(f"30-day avg: ${avg_recent:.0f}")
        for price_val, date_str, price_str in recent[1:4]:
            lines.append(f"  • {price_str} — {date_str}")
        if len(recent) < 3:
            lines.append(f"  Low volume — {len(recent)} sale(s) found")
    return "\n".join(lines)


def build_hype_radar_section(title, emoji, subreddit, watchlist, token):
    lines = [f"\n━━━━━━━━━━━━━━━", f"{emoji} HYPE RADAR — {title}", "━━━━━━━━━━━━━━━"]
    reddit_mentions = {}
    try:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
        r = requests.get(url, headers={"User-Agent": "CardBriefingBot/1.0"}, timeout=10)
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
        if mentions < 3:
            continue
        recent_sales = get_sold_listings(query, token, 7)
        prior_sales  = get_sold_listings(query, token, 14)
        prior_sales  = [s for s in prior_sales if s not in recent_sales]
        recent_count = len(recent_sales)
        prior_count  = max(len(prior_sales), 1)
        volume_pct   = ((recent_count - prior_count) / prior_count) * 100
        if volume_pct >= 50:
            hype_cards.append((name, mentions, volume_pct, recent_sales))
    if not hype_cards:
        lines.append("No hype signals today.")
    else:
        for name, mentions, vol_pct, recent_sales in hype_cards:
            lines.append(f"\n{name}")
            lines.append(f"Reddit mentions (24hr): {mentions}")
            lines.append(f"eBay volume spike: +{vol_pct:.0f}%")
            for price_val, date_str, price_str in recent_sales[:3]:
                lines.append(f"  • {price_str} — {date_str}")
    return "\n".join(lines)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def build_message():
    now_est = datetime.utcnow() - timedelta(hours=5)
    today   = now_est.strftime("%a %b %-d")
    lines   = [f"📈 CARD BRIEFING — {today}"]
    try:
        token = get_ebay_token()
    except Exception as e:
        return f"📈 CARD BRIEFING — {today}\n\nFailed to get eBay token: {e}"
    lines.append(build_my_cards_section(token))
    lines.append(build_watchlist_section("ONE PIECE WATCHLIST", "🏴‍☠️", ONE_PIECE_WATCHLIST, token))
    lines.append(build_watchlist_section("POKEMON WATCHLIST", "⚡", POKEMON_WATCHLIST, token))
    lines.append(build_hype_radar_section("ONE PIECE", "🔥", "OnePieceTCG", ONE_PIECE_WATCHLIST, token))
    lines.append(build_hype_radar_section("POKEMON", "🔥", "PokemonTCG", POKEMON_WATCHLIST, token))
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
