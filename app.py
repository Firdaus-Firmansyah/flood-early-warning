from flask import Flask, render_template, request, jsonify
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

app = Flask(__name__)

# --- SETUP FUZZY LOGIC ---
def setup_fuzzy():
    curah_hujan = ctrl.Antecedent(np.arange(0, 151, 1), 'curah_hujan')
    tinggi_air = ctrl.Antecedent(np.arange(0, 301, 1), 'tinggi_air')
    status = ctrl.Consequent(np.arange(0, 101, 1), 'status')

    curah_hujan['ringan'] = fuzz.trimf(curah_hujan.universe, [0, 0, 50])
    curah_hujan['sedang'] = fuzz.trimf(curah_hujan.universe, [20, 50, 100])
    curah_hujan['lebat']  = fuzz.trimf(curah_hujan.universe, [80, 150, 150])

    tinggi_air['normal'] = fuzz.trimf(tinggi_air.universe, [0, 0, 100])
    tinggi_air['siaga']  = fuzz.trimf(tinggi_air.universe, [80, 150, 250])
    tinggi_air['bahaya'] = fuzz.trimf(tinggi_air.universe, [200, 300, 300])

    status['aman']    = fuzz.trimf(status.universe, [0, 0, 30])
    status['waspada'] = fuzz.trimf(status.universe, [20, 40, 60])
    status['siaga']   = fuzz.trimf(status.universe, [50, 70, 90])
    status['awas']    = fuzz.trimf(status.universe, [80, 100, 100])

    # 9 Rules
    rule1 = ctrl.Rule(curah_hujan['ringan'] & tinggi_air['normal'], status['aman'])
    rule2 = ctrl.Rule(curah_hujan['ringan'] & tinggi_air['siaga'], status['waspada'])
    rule3 = ctrl.Rule(curah_hujan['ringan'] & tinggi_air['bahaya'], status['siaga'])
    
    rule4 = ctrl.Rule(curah_hujan['sedang'] & tinggi_air['normal'], status['waspada'])
    rule5 = ctrl.Rule(curah_hujan['sedang'] & tinggi_air['siaga'], status['siaga'])
    rule6 = ctrl.Rule(curah_hujan['sedang'] & tinggi_air['bahaya'], status['awas'])
    
    rule7 = ctrl.Rule(curah_hujan['lebat'] & tinggi_air['normal'], status['siaga'])
    rule8 = ctrl.Rule(curah_hujan['lebat'] & tinggi_air['siaga'], status['awas'])
    rule9 = ctrl.Rule(curah_hujan['lebat'] & tinggi_air['bahaya'], status['awas'])

    sistem_kontrol = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9])
    return sistem_kontrol

sistem_kontrol = setup_fuzzy()

import time
import re
import threading
import urllib.request
import xml.etree.ElementTree as ET

# --- BMKG CAP ALERTS CONFIGURATION & CACHE ---
ALERT_CACHE = {
    'id': {
        'timestamp': 0,
        'data': []
    },
    'en': {
        'timestamp': 0,
        'data': []
    }
}
CACHE_LOCK = threading.Lock()
CACHE_EXPIRY_SECONDS = 90  # Cache for 1.5 minutes to prevent hitting the 60 requests/min rate limit

def parse_cap_xml(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
        
        identifier = root.find('cap:identifier', ns)
        identifier = identifier.text if identifier is not None else ""
        
        sender = root.find('cap:sender', ns)
        sender = sender.text if sender is not None else ""
        
        sent = root.find('cap:sent', ns)
        sent = sent.text if sent is not None else ""
        
        status = root.find('cap:status', ns)
        status = status.text if status is not None else ""
        
        msg_type = root.find('cap:msgType', ns)
        msg_type = msg_type.text if msg_type is not None else ""
        
        scope = root.find('cap:scope', ns)
        scope = scope.text if scope is not None else ""
        
        info_elem = root.find('cap:info', ns)
        if info_elem is None:
            return None
            
        info = {}
        for tag in ['language', 'category', 'event', 'urgency', 'severity', 'certainty', 
                     'effective', 'expires', 'senderName', 'headline', 'description', 'web', 'instruction']:
            elem = info_elem.find(f'cap:{tag}', ns)
            info[tag] = elem.text if elem is not None else ""
            
        # Get area details
        area_elem = info_elem.find('cap:area', ns)
        area = {}
        if area_elem is not None:
            desc_elem = area_elem.find('cap:areaDesc', ns)
            area['areaDesc'] = desc_elem.text if desc_elem is not None else ""
            
            polygons = []
            for poly in area_elem.findall('cap:polygon', ns):
                if poly.text:
                    polygons.append(poly.text.strip())
            area['polygons'] = polygons
        else:
            area['areaDesc'] = ""
            area['polygons'] = []
            
        info['area'] = area
        
        # Extract kecamatan (subdistricts) from description
        info['kecamatan'] = extract_kecamatan(info['description'], info['language'])
        
        return {
            'identifier': identifier,
            'sender': sender,
            'sent': sent,
            'status': status,
            'msgType': msg_type,
            'scope': scope,
            'info': info
        }
    except Exception as e:
        print("Error parsing CAP XML:", e)
        return None

def extract_kecamatan(description, lang='id'):
    if not description:
        return []
    desc = description.strip()
    
    # Define regex patterns for finding where the list of kecamatan starts
    pattern_id = r'(?:khususnya di|meliputi wilayah|meliputi|terdampak di)\s+([^.]+)'
    pattern_en = r'(?:especially in|covering|including|in)\s+([^.]+)'
    
    pattern = pattern_id if lang == 'id' else pattern_en
    match = re.search(pattern, desc, re.IGNORECASE)
    if match:
        kec_text = match.group(1)
        # Take only the first sentence/line if there's multiple
        kec_text = kec_text.split('\n')[0]
        # Split by comma or "dan" / "and"
        parts = re.split(r',|dan|and', kec_text)
        kec_list = []
        for p in parts:
            p_clean = p.strip().strip('.')
            # Remove any unwanted description filler words
            if p_clean and len(p_clean) > 2 and not any(word in p_clean.lower() for word in ['kondisi', 'potensi', 'masyarakat', 'himbauan', 'cuaca', 'berpotensi', 'wilayah', 'sebagian']):
                kec_list.append(p_clean)
        return kec_list
    return []

def fetch_rss_and_details(lang='id'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*'
    }
    rss_url = f'https://www.bmkg.go.id/alerts/nowcast/{lang}'
    
    req = urllib.request.Request(rss_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            rss_xml = response.read()
    except Exception as e:
        print(f"Error fetching RSS feed ({lang}):", e)
        return None
        
    try:
        root = ET.fromstring(rss_xml)
    except Exception as e:
        print(f"Error parsing RSS XML ({lang}):", e)
        return None
        
    items = root.findall('.//item')
    alerts_list = []
    
    for item in items:
        title = item.find('title')
        title = title.text if title is not None else ""
        
        link = item.find('link')
        link = link.text if link is not None else ""
        
        pubDate = item.find('pubDate')
        pubDate = pubDate.text if pubDate is not None else ""
        
        guid = item.find('guid')
        guid = guid.text if guid is not None else ""
        
        detail_data = None
        if link:
            try:
                # Small delay to prevent hammering BMKG server sequentially
                time.sleep(0.05)
                req_detail = urllib.request.Request(link, headers=headers)
                with urllib.request.urlopen(req_detail) as resp:
                    detail_xml = resp.read()
                    detail_data = parse_cap_xml(detail_xml)
            except Exception as e:
                print(f"Error fetching CAP detail from {link}:", e)
                
        alerts_list.append({
            'title': title,
            'link': link,
            'pubDate': pubDate,
            'guid': guid,
            'detail': detail_data
        })
        
    return alerts_list

def get_alerts(lang='id'):
    global ALERT_CACHE
    if lang not in ['id', 'en']:
        lang = 'id'
        
    current_time = time.time()
    
    with CACHE_LOCK:
        cache = ALERT_CACHE[lang]
        if current_time - cache['timestamp'] > CACHE_EXPIRY_SECONDS or not cache['data']:
            print(f"Cache expired/empty for BMKG alerts ({lang}). Reloading from BMKG...")
            fresh_data = fetch_rss_and_details(lang)
            if fresh_data is not None:
                cache['data'] = fresh_data
                cache['timestamp'] = current_time
            else:
                print("Failed to fetch fresh data. Serving stale cache if available.")
        return cache['data']

@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    lang = request.args.get('lang', 'id')
    try:
        alerts = get_alerts(lang)
        return jsonify({
            "status": "success",
            "count": len(alerts),
            "data": alerts,
            "source": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
            "cached_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ALERT_CACHE[lang]['timestamp']))
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    
    ch_val = float(data.get('curah_hujan', 0))
    ta_val = float(data.get('tinggi_air', 0))
    
    simulasi_banjir = ctrl.ControlSystemSimulation(sistem_kontrol)
    simulasi_banjir.input['curah_hujan'] = ch_val
    simulasi_banjir.input['tinggi_air'] = ta_val
    
    try:
        simulasi_banjir.compute()
        indeks_bahaya = round(simulasi_banjir.output['status'], 2)
    except Exception as e:
        # Menghindari error jika nilai di luar bounds atau kasus edge
        indeks_bahaya = 0.0

    # Menentukan status dan tema warna
    if indeks_bahaya >= 80:
        status_text = "DANGER"
        color_theme = "bg-red-500 text-white"
    elif indeks_bahaya >= 50:
        status_text = "CAUTION"
        color_theme = "bg-orange-500 text-white"
    elif indeks_bahaya >= 20:
        status_text = "WARNING"
        color_theme = "bg-yellow-400 text-gray-900"
    else:
        status_text = "SAFE"
        color_theme = "bg-green-500 text-white"

    return jsonify({
        "indeks": indeks_bahaya,
        "status_text": status_text,
        "color_theme": color_theme
    })

if __name__ == '__main__':
    app.run(debug=True)