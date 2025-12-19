import os
import json
import requests
from dotenv import load_dotenv
import time

# --- CONFIGURATION ---
load_dotenv()
DEMO_MODE = False 

# --- HARDCODED BACKUP DATA (Bulletproof for Demo) ---
BACKUP_DATA = {
    "ai": { # Keyword to match
        "topic": "AI Regulation",
        "critic": {
            "title": "Stifling Innovation",
            "points": ["Strict rules may slow down technological progress.", "Small startups cannot afford compliance costs.", "Other countries might overtake us in AI development."]
        },
        "facts": {
            "title": "Global Policy Status",
            "points": ["EU AI Act is the world's first comprehensive AI law.", "US Executive Order requires safety testing for models.", "China has implemented strict algorithm registry rules."]
        },
        "proponent": {
            "title": "Safety & Ethics",
            "points": ["Prevents deepfakes and misinformation spread.", "Protects user privacy and data rights.", "Ensures AI systems align with human values."]
        }
    },
    "crypto": { # Keyword to match
        "topic": "Crypto Regulation",
        "critic": {
            "title": "Financial Risk",
            "points": ["High volatility puts investors at risk.", "Lack of consumer protection mechanism.", "Energy consumption concerns for mining."]
        },
        "facts": {
            "title": "Market Data",
            "points": ["Bitcoin ETF approval increased institutional access.", "Total market cap fluctuates around $2 Trillion.", "El Salvador holds Bitcoin as legal tender."]
        },
        "proponent": {
            "title": "Decentralization",
            "points": ["Removes reliance on central banks.", "Lowers cost of international transfers.", "Provides financial access to unbanked populations."]
        }
    }
}

# --- GENERIC FALLBACK (If topic is unknown) ---
def get_mock_data(topic):
    time.sleep(1)
    return {
        "topic": topic,
        "critic": { "title": "Critical View", "points": ["Concerns about safety", "High costs", "Regulation issues"] },
        "facts": { "title": "The Data", "points": ["Adoption up by 20%", "Passed Senate vote", "Global impact study"] },
        "proponent": { "title": "Positive View", "points": ["Innovation driver", "Economic growth", "Sustainability"] }
    }

# --- REAL FUNCTIONS ---
def fetch_news(topic):
    api_key = os.getenv("GNEWS_API_KEY")
    url = f"https://gnews.io/api/v4/search?q={topic}&lang=en&max=5&apikey={api_key}"
    try:
        response = requests.get(url).json()
        articles = response.get('articles', [])
        if not articles: return None
        full_text = ""
        for art in articles:
            full_text += f"Title: {art['title']}. Summary: {art['description']}\n"
        return full_text
    except Exception as e:
        print(f"News Error: {e}")
        return None

# --- DYNAMIC MODEL FINDER ---
def get_working_model_name(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        data = requests.get(url).json()
        for model in data.get('models', []):
            if 'generateContent' in model['supportedGenerationMethods']:
                if 'flash' in model['name']:
                    return model['name'].replace("models/", "")
        if 'models' in data:
            return data['models'][0]['name'].replace("models/", "")
    except:
        pass
    return "gemini-1.5-flash"

class ModelWrapper:
    def __init__(self, name):
        self.model_name = name

model = ModelWrapper("Auto-Detect") # Placeholder

def analyze_with_gemini(topic, news_text):
    api_key = os.getenv("GOOGLE_API_KEY")
    real_model_name = get_working_model_name(api_key)
    model.model_name = real_model_name # Update global tracker
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{real_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt_text = f"""
    Analyze this news about '{topic}'. 
    Strictly split the response into 3 sections: CRITIC (Negative), FACTS (Neutral), PROPONENT (Positive).
    Return ONLY valid JSON in this format:
    {{
        "topic": "{topic}",
        "critic": {{ "title": "Main Concern", "points": ["point 1", "point 2", "point 3"] }},
        "facts": {{ "title": "Key Data", "points": ["stat 1", "stat 2", "stat 3"] }},
        "proponent": {{ "title": "Main Benefit", "points": ["point 1", "point 2", "point 3"] }}
    }}
    
    News Text:
    {news_text}
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
def get_analysis(topic):
    # 1. HANDLE DEMO MODE (HARDCODED)
    if DEMO_MODE:
        user_input = topic.lower()
        
        # Check if "ai" is in the input (e.g., "AI Regulations", "ai safety")
        if "ai" in user_input:
            return BACKUP_DATA["ai"]
            
        # Check if "crypto" is in the input
        if "crypto" in user_input or "bitcoin" in user_input:
            return BACKUP_DATA["crypto"]
            
        # Default fallback
        return get_mock_data(topic)

    # 2. REAL ONLINE MODE
    print(f"Fetching news for {topic}...")
    news_text = fetch_news(topic)
    
    if not news_text:
        return {"error": "No news found. Check GNews API Key or quota."}
        
    print("Analyzing with Gemini...")
    result = analyze_with_gemini(topic, news_text)
    
    if not result:
        return {"error": "AI failed to analyze."}
        
    return result