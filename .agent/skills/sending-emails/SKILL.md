---
name: sending-emails
description: How to send emails programmatically using Red Mail (Python)
---

# Sending Emails with Red Mail

Red Mail is a Python library for sending emails via SMTP. It supports HTML/text bodies, attachments, embedded images/plots/tables, and Jinja templating.

- **Docs**: https://red-mail.readthedocs.io/
- **Repo**: https://github.com/Miksus/red-mail
- **Install**: `uv add redmail` or `pip install redmail`

## Setup

```python
from redmail import EmailSender

email = EmailSender(
    host="smtp.gmail.com",
    port=587,
    username="me@example.com",
    password="<APP_PASSWORD>",
)
```

For Gmail, use an [App Password](https://myaccount.google.com/apppasswords).

## Simple Send

```python
email.send(
    subject="An email",
    sender="me@example.com",
    receivers=["you@example.com"],
    text="Hi, this is an email.",
    html="<h1>Hi,</h1><p>this is an email.</p>",
)
```

## Attachments

```python
from pathlib import Path
import pandas as pd

email.send(
    subject="Email subject",
    sender="me@example.com",
    receivers=["you@example.com"],
    text="Hi, this is a simple email.",
    attachments={
        "myfile.csv": Path("path/to/data.csv"),
        "myfile.xlsx": pd.DataFrame({"A": [1, 2, 3]}),
        "myfile.html": "<h1>This is content of an attachment</h1>",
    },
)
```

## Embedded Images

```python
email.send(
    subject="Email subject",
    sender="me@example.com",
    receivers=["you@example.com"],
    html="""
        <h1>Hi,</h1>
        <p>have you seen this?</p>
        {{ myimg }}
    """,
    body_images={"myimg": "path/to/my/image.png"},
)
```

## Embedded Plots

```python
import matplotlib.pyplot as plt

fig = plt.figure()
plt.plot([1, 2, 3, 2, 3])

email.send(
    subject="Email subject",
    sender="me@example.com",
    receivers=["you@example.com"],
    html="""
        <h1>Hi,</h1>
        <p>have you seen this?</p>
        {{ myplot }}
    """,
    body_images={"myplot": fig},
)
```

## Embedded Tables

```python
import pandas as pd

email.send(
    subject="Email subject",
    sender="me@example.com",
    receivers=["you@example.com"],
    html="""
        <h1>Hi,</h1>
        <p>have you seen this?</p>
        {{ mytable }}
    """,
    body_tables={"mytable": pd.DataFrame({"a": [1, 2, 3], "b": [1, 2, 3]})},
)
```

## Jinja Parametrization

```python
email.send(
    subject="Email subject",
    sender="me@example.com",
    receivers=["you@example.com"],
    text="Hi {{ friend }}, nice to meet you.",
    html="<h1>Hi {{ friend }}, nice to meet you</h1>",
    body_params={"friend": "Jack"},
)
```

## Email with Multiple Images

```python
body_images = {
    f'plot_{i+1}': {
        "content": fig,
        'subtype': 'png',
        'maintype': 'image',
        'filename': f'plot_{i+1}.png'
    } for i, fig in enumerate(fig_list)
}

email.send(
    subject=subject,
    sender=sender,
    receivers=receivers,
    html="""
        <p>{{ bodytext }}</p>
        {{ plot_1 }}
        {{ plot_2 }}
        {{ plot_3 }}
    """,
    body_params={
        "bodytext": bodytext,
    },
    body_images=body_images,
)
```

## Full Example

```python
from pathlib import Path
from redmail import EmailSender
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt

fig = plt.figure()
plt.plot([1, 2, 3])

df = pd.DataFrame({"A": [1, 2, 3], "B": [1, 2, 3]})
byte_content = Path("a_file.bin").read_bytes()

email.send(
    subject="A lot of stuff!",
    sender="me@example.com",
    receivers=["you@example.com"],
    cc=["also@example.com"],
    bcc=["external@example.com"],
    text="""Hi {{ friend }},
    This email has a lot of stuff!
    Use HTML to view the awesome content.
    """,
    html="""<h1>Hi {{ friend }},</h1>
    <p>This email has a lot of stuff!</p>
    <p>Like this image:</p>
    {{ my_image }}
    <p>or this plot:</p>
    {{ my_plot }}
    <p>or this table:</p>
    {{ my_table }}
    <p>or this loop:</p>
    <ul>
    {% for value in container %}
        {% if value > 5 %}
            <li>{{ value }}</li>
        {% else %}
            <li style="color: red">{{ value }}</li>
        {% endif %}
    {% endfor %}
    </ul>
    """,
    body_images={
        "my_image": "path/to/image.png",
        "my_pillow": Image.new("RGB", (100, 30), color=(73, 109, 137)),
        "my_plot": fig,
    },
    body_tables={"my_table": df},
    body_params={
        "friend": "Jack",
        "container": [1, 3, 5, 7, 9],
    },
    attachments={
        "data.csv": df,
        "file.txt": "This is file content",
        "file.html": Path("path/to/a_file.html"),
        "file.bin": byte_content,
    },
)
```
