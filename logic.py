import os
import json
import requests
from dotenv import load_dotenv
import time

# --- CONFIGURATION ---
load_dotenv()
DEMO_MODE = False 

# --- HARDCODED BACKUP DATA ---
BACKUP_DATA = {
    "ai": {
        "topic": "AI Regulation",
        "critic": { "title": "Stifling Innovation", "points": ["Strict rules may slow down technological progress.", "Small startups cannot afford compliance costs.", "Geopolitical rivals might overtake us in AI."] },
        "facts": { "title": "Global Policy Status", "points": ["EU AI Act is the world's first comprehensive AI law.", "US Executive Order requires safety testing for models.", "China has implemented strict algorithm registry rules."] },
        "proponent": { "title": "Safety & Ethics", "points": ["Prevents deepfakes and misinformation spread.", "Protects user privacy and data rights.", "Ensures AI systems align with human values."] }
    },
    "crypto": {
        "topic": "Crypto Regulation",
        "critic": { "title": "Financial Risk", "points": ["High volatility puts retail investors at risk.", "Lack of consumer protection mechanisms.", "Energy consumption concerns for mining."] },
        "facts": { "title": "Market Data", "points": ["Bitcoin ETF approval increased institutional access.", "Total market cap fluctuates around $2 Trillion.", "El Salvador holds Bitcoin as legal tender."] },
        "proponent": { "title": "Decentralization", "points": ["Removes reliance on central banks.", "Lowers cost of international transfers.", "Provides financial access to unbanked populations."] }
    },
    "climate": {
        "topic": "Climate Policy",
        "critic": { "title": "Economic Impact", "points": ["Transition costs may spike energy prices.", "Developing nations need financial support.", "Risk of job losses in traditional energy sectors."] },
        "facts": { "title": "Global Targets", "points": ["Paris Agreement aims to limit warming to 1.5°C.", "Renewable energy investment hit $1.8 Trillion in 2023.", "Carbon pricing adopted by 70+ jurisdictions."] },
        "proponent": { "title": "Sustainability", "points": ["Mitigates extreme weather events.", "Creates millions of new green jobs.", "Reduces long-term healthcare costs from pollution."] }
    },
    "ev": {
        "topic": "EV Transition",
        "critic": { "title": "Infrastructure Gaps", "points": ["Charging station network is still insufficient.", "Battery disposal poses environmental risks.", "High upfront cost for consumers."] },
        "facts": { "title": "Industry Shift", "points": ["EV sales surpassed 14 million units globally in 2023.", "Major automakers pledging 100% electric by 2035.", "Battery costs have dropped 90% since 2010."] },
        "proponent": { "title": "Clean Transport", "points": ["Drastically reduces tailpipe emissions.", "Lowers dependence on imported oil.", "Lower maintenance costs for owners."] }
    }
}

# --- HELPER: GET MODEL NAME ---
def get_working_model_name(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        data = requests.get(url).json()
        for model in data.get('models', []):
            if 'generateContent' in model['supportedGenerationMethods']:
                if 'flash' in model['name']: return model['name'].replace("models/", "")
        if 'models' in data: return data['models'][0]['name'].replace("models/", "")
    except: pass
    return "gemini-1.5-flash"

class ModelWrapper:
    def __init__(self, name): self.model_name = name

model = ModelWrapper("Auto-Detect") 

# --- AI QUERY OPTIMIZER ---
def optimize_search_query(raw_topic):
    """
    Asks AI for the best 'News Keyword'.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    real_model_name = get_working_model_name(api_key)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{real_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt_text = f"""
    You are a Search Expert.
    User Input: "{raw_topic}"
    Task: Convert this into the **single best 2-3 word English search term** to find recent news articles.
    If it's a local Indian event like "tvk maanadu", output "Vijay TVK" or "Tamizhaga Vettri Kazhagam".
    OUTPUT ONLY THE KEYWORD. NO EXPLANATION.
    """
    
    payload = { "contents": [{ "parts": [{"text": prompt_text}] }] }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            optimized_query = result['candidates'][0]['content']['parts'][0]['text'].strip()
            if optimized_query: return optimized_query
    except:
        pass
    
    return raw_topic 

# --- REAL FUNCTIONS ---
def fetch_news_internal(query, region_code, api_key):
    url = f"https://gnews.io/api/v4/search?q={query}&max=5&apikey={api_key}"
    if region_code:
        url += f"&country={region_code}"
        
    try:
        response = requests.get(url).json()
        articles = response.get('articles', [])
        if not articles: return None
        
        full_text = ""
        for art in articles:
            full_text += f"Source: {art['source']['name']} - Title: {art['title']}. Summary: {art['description']}\n"
        return full_text
    except:
        return None

def fetch_news(topic, region="Global"):
    api_key = os.getenv("GNEWS_API_KEY")
    country_map = { "India": "in", "USA": "us", "UK": "gb", "Australia": "au", "Canada": "ca", "Europe": "fr", "Asia": "jp" }
    region_code = country_map.get(region, None)

    # 1. ATTEMPT A: AI Optimized (e.g. "Tamizhaga Vettri Kazhagam")
    optimized_query = optimize_search_query(topic)
    print(f"Attempt 1 (AI): '{optimized_query}'")
    news_text = fetch_news_internal(optimized_query, region_code, api_key)
    if news_text: return news_text, optimized_query

    # 2. ATTEMPT B: Raw Input (e.g. "tvk maanadu")
    print(f"Attempt 2 (Raw): '{topic}'")
    news_text = fetch_news_internal(topic, region_code, api_key)
    if news_text: return news_text, topic

    # 3. ATTEMPT C: Smart Fallbacks (Hardcoded safety net)
    fallback_query = None
    if "tvk" in topic.lower(): fallback_query = "Vijay TVK"
    elif "vijay" in topic.lower(): fallback_query = "Tamil Actor Vijay"
    
    if fallback_query:
        print(f"Attempt 3 (Fallback): '{fallback_query}'")
        news_text = fetch_news_internal(fallback_query, region_code, api_key)
        if news_text: return news_text, fallback_query

    # 4. ATTEMPT D: Global Search (Last Resort)
    if region != "Global":
        print(f"Attempt 4 (Global): '{optimized_query}'")
        news_text = fetch_news_internal(optimized_query, None, api_key)
        if news_text: return news_text, optimized_query

    return "NO_ARTICLES_FOUND", optimized_query

# --- MAIN ANALYSIS FUNCTION ---
def analyze_with_gemini(topic, news_text, intensity="Standard"):
    api_key = os.getenv("GOOGLE_API_KEY")
    real_model_name = get_working_model_name(api_key)
    model.model_name = real_model_name 
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{real_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    tone_instruction = "Be balanced and objective."
    if intensity == "Skeptical": tone_instruction = "Be highly critical."
    elif intensity == "Ruthless": tone_instruction = "Be ruthless. Expose every weakness."
    
    prompt_text = f"""
    Analyze this news about '{topic}'. {tone_instruction}
    IMPORTANT: Translate insights into English if source is local.
    Strictly split response into 3 sections: CRITIC, FACTS, PROPONENT.
    Return ONLY valid JSON:
    {{
        "topic": "{topic}",
        "critic": {{ "title": "Main Concern", "points": ["p1", "p2", "p3"] }},
        "facts": {{ "title": "Key Data", "points": ["s1", "s2", "s3"] }},
        "proponent": {{ "title": "Main Benefit", "points": ["p1", "p2", "p3"] }}
    }}
    News Text: {news_text}
    """
    
    payload = { "contents": [{ "parts": [{"text": prompt_text}] }] }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200: return None
        result = response.json()
        raw_text = result['candidates'][0]['content']['parts'][0]['text']
        clean_json = raw_text.replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        print(f"Direct Connection Error: {e}")
        return None

# --- EXPORT FUNCTION ---
def get_analysis(topic, settings=None):
    if settings is None: settings = {"region": "Global", "intensity": "Standard"}

    # DEMO MODE
    if DEMO_MODE:
        t = topic.lower()
        if any(x in t for x in ["ai", "artificial"]): return BACKUP_DATA["ai"]
        if any(x in t for x in ["crypto", "btc"]): return BACKUP_DATA["crypto"]
        if any(x in t for x in ["climate", "warming"]): return BACKUP_DATA["climate"]
        if any(x in t for x in ["ev", "electric", "tesla"]): return BACKUP_DATA["ev"]
        return BACKUP_DATA["ai"] # Fallback

    # ONLINE MODE
    print(f"Fetching news for {topic} in {settings['region']}...")
    news_text, used_query = fetch_news(topic, settings['region'])
    
    if news_text == "NO_ARTICLES_FOUND":
        return {"error": f"No news found for '{topic}'. Try switching Region to 'Global'."}
    
    if not news_text:
        return {"error": "API Connection Failed."}
        
    print(f"Analyzing '{used_query}'...")
    result = analyze_with_gemini(used_query, news_text, settings['intensity'])
    
    if not result:
        return {"error": "AI failed to analyze."}
        
    return result