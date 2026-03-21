"""
mailer.py — Email notifications for Daily Reader.

Sends a daily teaser email with links to the generated reading pages.
"""

from __future__ import annotations

import datetime
import os

from dotenv import load_dotenv
from redmail import EmailSender

load_dotenv()

EMAIL_TO = "keoliyamayank@gmail.com"
EMAIL_FROM = "keoliyamayank@gmail.com"
FEED_LINK = "https://mkeoliya.github.io/daily-reader/"


def send_email(items: list[dict]):
    """Send a teaser email with links to today's reading pages.

    Args:
        items: List of dicts with 'title' and 'page_url' keys.
    """
    gmail = EmailSender(
        host="smtp.gmail.com",
        port=587,
        username=EMAIL_FROM,
        password=os.environ["GMAIL_APP_PASSWORD"],
    )

    links_html = ""
    for item in items:
        url = item.get("page_url", FEED_LINK)
        links_html += f'<li><a href="{url}">{item["title"]}</a></li>\n'

    today = datetime.date.today().strftime("%B %d, %Y")
    html_body = f"""\
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; color: #333; }}
  h1 {{ font-size: 1.3em; }}
  ul {{ padding-left: 1.2em; }}
  li {{ margin-bottom: 0.5em; }}
  a {{ color: #2d5a8e; }}
  .footer {{ font-size: 0.8em; color: #999; margin-top: 2em; border-top: 1px solid #eee; padding-top: 1em; }}
</style>
</head>
<body>
  <h1>📖 Daily Reader</h1>
  <p>{len(items)} new page(s) — {today}</p>
  <ul>
    {links_html}
  </ul>
  <p><a href="{FEED_LINK}">Read on Daily Reader →</a></p>
  <p class="footer">Sent by Daily Reader</p>
</body>
</html>"""

    gmail.send(
        subject=f"📖 Daily Reader — {items[0]['title']}",
        receivers=[EMAIL_TO],
        html=html_body,
    )
    print(f"  ✉ Email sent to {EMAIL_TO}")
