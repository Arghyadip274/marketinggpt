import json
from app.tools.website_analyzer import WebsiteSEOAnalyzer

def main():
    analyzer = WebsiteSEOAnalyzer()
    print("Testing example.com...")
    result = analyzer.analyze("https://www.hubspot.com")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
