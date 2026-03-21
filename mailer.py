"""
mailer.py — Email notifications for Daily Reader.

Sends a daily teaser email with the first section's content embedded.
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


def send_email(section_name: str, documents: list[dict], page_url: str):
    """Send a teaser email with the first section's content.

    Args:
        section_name: Name of the first section (e.g. "ml").
        documents: List of dicts with 'title', 'page_info', 'body_html'.
        page_url: URL to the full daily page.
    """
    gmail = EmailSender(
        host="smtp.gmail.com",
        port=587,
        username=EMAIL_FROM,
        password=os.environ["GMAIL_APP_PASSWORD"],
    )

    # Build content from first section's documents
    content_html = ""
    for doc in documents:
        content_html += f"<h2>{doc['title']}</h2>\n"
        content_html += f"<p style='color: #666; font-size: 0.9em;'>{doc['page_info']}</p>\n"
        content_html += doc["body_html"]

    today = datetime.date.today().strftime("%B %d, %Y")
    subject_title = documents[0]["title"] if documents else section_name

    html_body = f"""\
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
  h1 {{ font-size: 1.3em; }}
  h2 {{ font-size: 1.1em; color: #2d5a8e; }}
  a {{ color: #2d5a8e; }}
  img {{ max-width: 100%; height: auto; }}
  .footer {{ font-size: 0.8em; color: #999; margin-top: 2em; border-top: 1px solid #eee; padding-top: 1em; }}
</style>
</head>
<body>
  <h1>📖 Daily Reader — {today}</h1>
  {content_html}
  <p><a href="{page_url}">Read all sections on Daily Reader →</a></p>
  <p class="footer">Sent by Daily Reader</p>
</body>
</html>"""

    gmail.send(
        subject=f"📖 Daily Reader — {subject_title}",
        receivers=[EMAIL_TO],
        html=html_body,
    )
    print(f"  ✉ Email sent to {EMAIL_TO}")
