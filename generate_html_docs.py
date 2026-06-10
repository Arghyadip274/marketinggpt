import os
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{TITLE}</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({ startOnLoad: false, theme: 'dark' });

        document.addEventListener('DOMContentLoaded', async () => {
            const rawMarkdown = document.getElementById('raw-markdown').textContent;
            // Parse markdown
            document.getElementById('content').innerHTML = marked.parse(rawMarkdown);
            
            // Convert language-mermaid code blocks to div.mermaid
            document.querySelectorAll('code.language-mermaid').forEach(el => {
                const pre = el.parentElement;
                const div = document.createElement('div');
                div.className = 'mermaid';
                div.textContent = el.textContent;
                pre.replaceWith(div);
            });
            
            // Render mermaid
            await mermaid.run();
        });
    </script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; 
            line-height: 1.6; 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 2rem; 
            background: #0d1117; 
            color: #c9d1d9; 
        }
        h1, h2, h3, h4 { color: #58a6ff; border-bottom: 1px solid #21262d; padding-bottom: 0.3em; margin-top: 1.5em; }
        h1 { font-size: 2.5em; }
        code { background: #161b22; padding: 0.2em 0.4em; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.9em; }
        pre code { background: none; padding: 0; }
        pre { background: #161b22; padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid #30363d; }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
        th, td { border: 1px solid #30363d; padding: 0.5rem 1rem; text-align: left; }
        th { background: #161b22; font-weight: 600; }
        blockquote { border-left: 4px solid #30363d; margin: 0; padding-left: 1rem; color: #8b949e; }
        .mermaid { text-align: center; margin: 2rem 0; background: #161b22; padding: 1rem; border-radius: 8px; border: 1px solid #30363d; }
    </style>
</head>
<body>
    <div id="content"></div>
    <!-- Use a hidden div to safely store raw markdown without script tag execution issues -->
    <div id="raw-markdown" style="display:none;">{MARKDOWN_CONTENT}</div>
</body>
</html>"""

def convert_docs():
    docs_dir = Path("project_docs")
    if not docs_dir.exists():
        print("project_docs directory not found!")
        return

    for md_file in docs_dir.glob("*.md"):
        print(f"Converting {md_file.name} to HTML...")
        content = md_file.read_text(encoding="utf-8")
        
        # Escape special HTML characters in markdown if needed, 
        # but using a hidden div with textContent is generally safe.
        # We replace any closing div tags just in case they appear in the markdown.
        safe_content = content.replace("</div>", "&lt;/div&gt;")
        
        html_content = HTML_TEMPLATE.replace("{TITLE}", md_file.stem).replace("{MARKDOWN_CONTENT}", safe_content)
        
        html_file = md_file.with_suffix(".html")
        html_file.write_text(html_content, encoding="utf-8")
        print(f"[SUCCESS] Generated: {html_file.name}")

if __name__ == "__main__":
    convert_docs()
