
import json
import re
import base64
from pathlib import Path

# PDF_DIAGRAM_V3
import markdown
import bleach

from html import escape
from urllib.parse import urlsplit
from pygments.formatters import HtmlFormatter
from playwright.sync_api import sync_playwright


ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "del", "ul", "ol", "li",
    "blockquote", "pre", "code", "a", "hr",
    "br", "table", "thead", "tbody", "tr",
    "th", "td", "div", "span"
]


def render_markdown(text):
    html = markdown.markdown(
        text,
        extensions=[
            "fenced_code",
            "tables",
            "codehilite",
            "sane_lists"
        ],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "codehilite"
            }
        }
    )

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes={
            "a": ["href", "title"],
            "div": ["class"],
            "span": ["class"],
            "code": ["class"],
            "pre": ["class"],
            "ol": ["start"]
        },
        protocols=["http", "https"],
        strip=True
    )


def generate_chat_pdf(title, messages):

    sections = []
    diagrams = []
    def diagram_placeholder(match):
        source = match.group(1).strip()
        index = len(diagrams)
        diagrams.append(source)
        return f'\n\n<div class="pdf-diagram-slot-{index}"></div>\n\n'


    for msg in messages:

        is_user = msg["role"] == "user"

        role = "You" if is_user else "Search AI Pro"

        if is_user:
            content = escape(msg["content"]).replace(
                "\n", "<br>"
            )
        else:
            content = render_markdown(re.sub(
                r"(?m)^ {0,3}```mermaid[ \t]*\n([\s\S]*?)^ {0,3}```[ \t]*$",
                diagram_placeholder, msg["content"], flags=re.I))

        source_links = []

        for source in json.loads(msg["sources"] or "[]"):

            url = source.get("url", "")

            try:
                parsed = urlsplit(url)
            except ValueError:
                continue

            if parsed.scheme not in ("http", "https"):
                continue

            if not parsed.netloc:
                continue

            name = source.get("title") or url

            source_links.append(
                f'<li><a href="{escape(url, quote=True)}">'
                f'{escape(name)}</a></li>'
            )

        sources = ""

        if source_links:
            sources = (
                '<div class="sources">'
                '<strong>Sources</strong><ul>'
                + "".join(source_links)
                + "</ul></div>"
            )

        role_class = "user" if is_user else "assistant"

        sections.append(
            f"""
            <section class="message {role_class}">
                <div class="role">{role}</div>
                <div class="content">{content}</div>
                {sources}
            </section>
            """
        )

    highlight_css = HtmlFormatter(
        style="github-dark"
    ).get_style_defs(".codehilite")

    css = """
        @page {
            size: A4;
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.65;
            color: #202938;
            background: white;
            overflow-wrap: anywhere;
        }

        .brand {
            font-size: 24pt;
            font-weight: bold;
            color: #6554d9;
        }

        .subtitle {
            color: #64748b;
            font-size: 10pt;
        }

        .chat-title {
            font-size: 21pt;
            margin: 22px 0;
            padding-bottom: 14px;
            border-bottom: 2px solid #6554d9;
        }

        .message {
            margin: 22px 0;
        }

        .role {
            font-size: 10pt;
            font-weight: bold;
            color: #6554d9;
            margin-bottom: 10px;
            break-after: avoid;
        }

        .user {
            background: #f0edff;
            border: 1px solid #ddd6fe;
            border-radius: 10px;
            padding: 14px;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #172033;
            line-height: 1.4;
            break-after: avoid;
            margin-top: 22px;
            margin-bottom: 10px;
        }

        h1 { font-size: 21pt; }
        h2 { font-size: 17pt; }
        h3 { font-size: 14pt; }
        h4 { font-size: 12pt; }

        p {
            margin: 10px 0;
            orphans: 3;
            widows: 3;
        }

        li {
            margin: 5px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 18px 0;
            font-size: 10pt;
        }

        thead {
            display: table-header-group;
        }

        th {
            background: #ece9ff;
            color: #252044;
            font-weight: bold;
        }

        th, td {
            border: 1px solid #d5dbe5;
            padding: 10px;
            text-align: left;
            vertical-align: top;
        }

        tr {
            break-inside: avoid;
        }

        tr:nth-child(even) {
            background: #f8fafc;
        }

        .codehilite {
            background: #0d1117;
            color: #c9d1d9;
            border-radius: 9px;
            padding: 14px;
            margin: 16px 0;
        }

        pre {
            font-family: Consolas, monospace;
            font-size: 9pt;
            line-height: 1.6;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            margin: 0;
            tab-size: 4;
        }

        pre code {
            font-family: inherit;
        }

        :not(pre) > code {
            background: #eef0f5;
            color: #5b21b6;
            padding: 2px 5px;
            border-radius: 4px;
            font-family: Consolas, monospace;
        }

        blockquote {
            border-left: 4px solid #6554d9;
            background: #f8fafc;
            padding: 10px 16px;
            margin: 14px 0;
        }

        hr {
            border: 0;
            border-top: 1px solid #d5dbe5;
            margin: 22px 0;
        }

        a {
            color: #5145cd;
            text-decoration: underline;
        }

        .sources {
            margin-top: 18px;
            font-size: 9pt;
            color: #64748b;
        }
    """

    css += """
        .pdf-diagram { break-inside: avoid; margin: 16px 0; text-align:center; }
        .pdf-diagram img { max-width:100%; max-height:220mm; object-fit:contain; }
        .pdf-brand-logo { width:64px; height:64px; vertical-align:middle; margin-right:12px; }
        table { table-layout:auto; overflow-wrap:normal; }
        th, td { overflow-wrap:break-word; }
    """
    logo_path = Path(__file__).resolve().parent / 'static/images/search-ai-logo.png'
    logo_data = base64.b64encode(logo_path.read_bytes()).decode('ascii')
    document = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Security-Policy"
              content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
        <title>{escape(title)}</title>
        <style>
            {css}
            {highlight_css}
        </style>
    </head>

    <body>
        <div class="brand"><img class="pdf-brand-logo" src="data:image/png;base64,{logo_data}" alt="">Search AI Pro</div>
        <div class="subtitle">
            AI Conversation Report
        </div>

        <div class="chat-title">
            {escape(title)}
        </div>

        {"".join(sections)}
    </body>
    </html>
    """

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        try:
            if diagrams:
                document = render_pdf_diagrams(browser, document, diagrams)
            page = browser.new_page(
                java_script_enabled=False
            )

            page.route("**/*", lambda route: route.abort())

            page.set_content(
                document,
                wait_until="load"
            )

            pdf = page.pdf(
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template="""
                    <div style="
                        width:100%;
                        font-size:9px;
                        color:#64748b;
                        text-align:center;
                        font-family:Arial;
                    ">
                        Search AI Pro |
                        Page <span class="pageNumber"></span>
                        of <span class="totalPages"></span>
                    </div>
                """,
                margin={
                    "top": "18mm",
                    "bottom": "20mm",
                    "left": "16mm",
                    "right": "16mm"
                }
            )

            return pdf

        finally:
            browser.close()



def render_pdf_diagrams(browser, document, diagrams):
    vendor = Path(__file__).resolve().parent / 'static/vendor'
    page = browser.new_page(viewport={'width': 1100, 'height': 900}, device_scale_factor=2)
    try:
        page.route('**/*', lambda route: route.abort())
        page.set_content('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'"><div id="diagram"></div>')
        page.add_script_tag(path=str(vendor / 'purify.min.js'))
        page.add_script_tag(path=str(vendor / 'mermaid/mermaid.min.js'))
        page.evaluate('''() => mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',maxTextSize:10000,maxEdges:100,flowchart:{htmlLabels:false,curve:'basis',nodeSpacing:45,rankSpacing:55},themeVariables:{primaryColor:'#dcfce7',primaryTextColor:'#14532d',primaryBorderColor:'#16a34a',secondaryColor:'#dbeafe',secondaryBorderColor:'#2563eb',tertiaryColor:'#ede9fe',lineColor:'#64748b',fontFamily:'Arial',fontSize:'15px'}})''')
        for i, source in enumerate(diagrams):
            slot = f'<div class="pdf-diagram-slot-{i}"></div>'
            fallback = '<pre>'+escape(source)+'</pre>'
            try:
                if len(source)>10000 or re.search(r'%%\{|^\s*---',source,re.M):
                    raise ValueError('Unsupported diagram configuration')
                source = re.sub(r'</?(?:b|strong|i|em|u)>','',source,flags=re.I)
                page.evaluate('''async ({source,id}) => {
                    const result = await mermaid.render(id,source);
                    const box = document.getElementById('diagram');
                    box.innerHTML = DOMPurify.sanitize(result.svg,{USE_PROFILES:{svg:true,svgFilters:true},FORBID_TAGS:['script','foreignObject','a','image'],FORBID_ATTR:['href','xlink:href']});
                    box.style.cssText='background:#f8fafc;padding:18px;width:fit-content;max-width:1060px;border-radius:12px';
                    const svg=box.querySelector('svg');
                    if(!svg) throw Error('No SVG');
                    svg.style.maxWidth='100%'; svg.style.height='auto';
                    svg.querySelectorAll('.node rect').forEach(n=>{n.setAttribute('rx','10');n.setAttribute('ry','10');});
                }''', {'source':source,'id':f'pdfdiagram{i}'})
                png=page.locator('#diagram').screenshot(timeout=10000)
                data=base64.b64encode(png).decode('ascii')
                replacement=f'<div class="pdf-diagram"><img alt="Diagram" src="data:image/png;base64,{data}"></div>'
            except Exception as exc:
                print(f'PDF diagram {i+1} failed: {type(exc).__name__}')
                replacement=fallback
            document=document.replace(slot,replacement,1)
    finally:
        page.close()
    return document
