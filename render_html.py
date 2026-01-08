import json
from collections import defaultdict
from astral import LocationInfo
from astral.sun import sun
from astral import moon
from datetime import datetime

# --- Visualization Logic ---
def interpolate_color(c1, c2, f):
    try:
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2-r1)*f)
        g = int(g1 + (g2-g1)*f)
        b = int(b1 + (b2-b1)*f)
        return f"#{r:02x}{g:02x}{b:02x}"
    except: return c1

def get_color(metric, val):
    scales = {
        'temp': [{'v':-10,'c':'#3b82f6'}, {'v':5,'c':'#06b6d4'}, {'v':20,'c':'#f59e0b'}, {'v':35,'c':'#ef4444'}],
        'wind': [{'v':0,'c':'#38bdf8'}, {'v':5,'c':'#22d3ee'}, {'v':10,'c':'#fbbf24'}, {'v':20,'c':'#f97316'}],
        'swell': [{'v':0,'c':'#0ea5e9'}, {'v':1,'c':'#22d3ee'}, {'v':2,'c':'#fbbf24'}, {'v':3,'c':'#ef4444'}],
        'otemp': [{'v':0,'c':'#3b82f6'}, {'v':10,'c':'#06b6d4'}, {'v':20,'c':'#f59e0b'}, {'v':30,'c':'#ef4444'}]
    }
    s = scales.get(metric, scales['wind'])
    if val <= s[0]['v']: return s[0]['c']
    if val >= s[-1]['v']: return s[-1]['c']
    for i in range(len(s)-1):
        if s[i]['v'] <= val <= s[i+1]['v']:
            c1, c2 = s[i]['c'], s[i+1]['c']
            f = (val - s[i]['v']) / (s[i+1]['v'] - s[i]['v'])
            return interpolate_color(c1, c2, f)
    return s[0]['c']

def get_moon_phase_emoji(date_obj):
    phase = moon.phase(date_obj)
    # 0:New, 7:1st Qtr, 14:Full, 21:Last Qtr
    if phase < 0.5 or phase >= 27.5: return '🌑'
    if phase < 6.5: return '🌒'
    if phase < 7.5: return '🌓'
    if phase < 13.5: return '🌔'
    if phase < 14.5: return '🌕'
    if phase < 20.5: return '🌖'
    if phase < 21.5: return '🌗'
    return '🌘'

def get_weather_icon(cloud, precip, hour, date_str, lat, lon):
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Shanghai")
        y, m, d_num = map(int, date_str.split('-'))
        date_obj = datetime(y, m, d_num, hour)
        city = LocationInfo("", "", "Asia/Shanghai", lat, lon)
        s = sun(city.observer, date=date_obj, tzinfo=tz)
        
        sunrise_hr = s['sunrise'].hour
        sunset_hr = s['sunset'].hour
        is_day = sunrise_hr <= hour < sunset_hr
    except:
        is_day = 7 <= hour < 19

    # 1. 降水判定 (优先)
    if precip > 0.5: return '🌧️'
    if precip > 0: return '🌦️'
    
    # 2. 云量判定
    if cloud > 75: return '☁️'
    if cloud > 25: return '⛅'
    
    # 3. 晴天/明朗判定 (区分昼夜)
    if is_day:
        return '☀️'
    else:
        try:
            return get_moon_phase_emoji(date_obj)
        except:
            return '🌙'

def create_wind_chart_svg(day_data, day_idx):
    if not day_data: return ""
    n = len(day_data)
    width = 800; height = 120
    padding_top = 10; padding_bottom = 25; padding_left = 30
    
    max_v = 15.0
    for _, v in day_data:
        max_v = max(max_v, float(v.get('wind_g',0) or 0), float(v.get('wind_s',0) or 0))
    max_v *= 1.1 
    
    def get_x(i): return padding_left + (i / (n-1)) * (width - padding_left) if n > 1 else padding_left
    def get_y(val): return height - (padding_bottom + (float(val or 0) / max_v) * (height - padding_top - padding_bottom))

    gust_pts = [f"{get_x(i)},{get_y(v.get('wind_g',0))}" for i, (_, v) in enumerate(day_data)]
    speed_pts = [f"{get_x(i)},{get_y(v.get('wind_s',0))}" for i, (_, v) in enumerate(day_data)]
    
    gust_area = f"M {padding_left},{height-padding_bottom} " + " L ".join(gust_pts) + f" L {width},{height-padding_bottom} Z"
    speed_area = f"M {padding_left},{height-padding_bottom} " + " L ".join(speed_pts) + f" L {width},{height-padding_bottom} Z"
    
    # Y-axis labels
    y_labels = ""
    for v in [0, 5, 10, 15]:
        if v <= max_v:
            y_pos = get_y(v)
            y_labels += f'<text x="{padding_left-5}" y="{y_pos+3}" text-anchor="end" class="chart-label-y">{v}</text>'
            y_labels += f'<line x1="{padding_left}" y1="{y_pos}" x2="{width}" y2="{y_pos}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />'

    labels_html = ""
    for i, (t, val) in enumerate(day_data):
        hour_str = t.split(":")[0].zfill(2)
        if i % 2 == 0:
            labels_html += f'<text x="{get_x(i)}" y="{height-5}" text-anchor="middle" class="chart-label">{hour_str}</text>'


    # Define vertical gradients for threshold coloring at 4m/s
    # Units are userSpaceOnUse to align with Y coordinates
    # y=get_y(0) is bottom, y=get_y(max_v) is top
    y_0 = height - padding_bottom
    y_max = padding_top
    y_4 = get_y(4)
    # Threshold percentage from bottom (y_0) to top (y_max)
    thresh_pct = (4 / max_v) * 100 if max_v > 0 else 0

    return f"""<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" class="wind-main-chart">
        <defs>
            <linearGradient id="gustGrad-{day_idx}" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#f97316;stop-opacity:0.3" />
                <stop offset="100%" style="stop-color:#f97316;stop-opacity:0.0" />
            </linearGradient>
            <!-- Vertical Color Shift for Speed Fill -->
            <linearGradient id="speedAreaGrad-{day_idx}" x1="0" y1="{y_0}" x2="0" y2="{y_max}" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.1" />
                <stop offset="{thresh_pct}%" stop-color="#22d3ee" stop-opacity="0.4" />
                <stop offset="{thresh_pct}%" stop-color="#00ff00" stop-opacity="0.4" />
                <stop offset="100%" stop-color="#00ff00" stop-opacity="0.5" />
            </linearGradient>
            <!-- Vertical Color Shift for Speed Stroke -->
            <linearGradient id="speedStrokeGrad-{day_idx}" x1="0" y1="{y_0}" x2="0" y2="{y_max}" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#22d3ee" />
                <stop offset="{thresh_pct}%" stop-color="#22d3ee" />
                <stop offset="{thresh_pct}%" stop-color="#00ff00" />
                <stop offset="100%" stop-color="#00ff00" />
            </linearGradient>
        </defs>
        {y_labels}
        <path d="{gust_area}" fill="url(#gustGrad-{day_idx})" class="animate-area" />
        <path d="{speed_area}" fill="url(#speedAreaGrad-{day_idx})" class="animate-area" />
        <path d="M {padding_left},{get_y(float(day_data[0][1].get('wind_g',0)))} {' L '.join(gust_pts)}" stroke="#f97316" stroke-width="2" fill="none" stroke-opacity="0.3" class="animate-path" />
        <path d="M {padding_left},{get_y(float(day_data[0][1].get('wind_s',0)))} {' L '.join(speed_pts)}" stroke="url(#speedStrokeGrad-{day_idx})" stroke-width="3" fill="none" class="animate-path" />
        {labels_html}
        <line x1="{padding_left}" y1="{height-padding_bottom}" x2="{padding_left}" y2="{padding_top}" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
    </svg>"""

def create_smooth_bar_segment(idx, day_data, key, min_v, max_v, base_color):
    n = len(day_data)
    cur = float(day_data[idx][1].get(key, 0) or 0)
    prev = float(day_data[idx-1][1].get(key, cur) or 0) if idx > 0 else cur
    nxt = float(day_data[idx+1][1].get(key, cur) or 0) if idx < n-1 else cur

    def norm(v): return min(100, max(0, (v - min_v) / (max_v - min_v) * 100))
    w_cur, w_prev, w_nxt = norm(cur), norm(prev), norm(nxt)
    
    w_top = (w_prev + w_cur) / 2
    w_bot = (w_cur + w_nxt) / 2
    
    path = f"M 0,0 L {w_top},0 Q {w_cur},50 {w_bot},100 L 0,100 Z"
    color = base_color if isinstance(base_color, str) else get_color(base_color[0], cur)
    
    return f"""<div class="smooth-bar-container">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <path d="{path}" fill="{color}" opacity="0.6"/>
        </svg>
    </div>"""

def generate_dashboard_content(weather_data, lat, lon):
    if not weather_data: return ""
    days = defaultdict(list)
    for k in sorted(weather_data.keys()):
        date_str, time_str = k.split(' ')
        days[date_str].append((time_str, weather_data[k]))
    
    cards_html = ""
    for d_idx, date_str in enumerate(sorted(days.keys())):
        day_data = days[date_str]
        chart_svg = create_wind_chart_svg(day_data, d_idx)
        
        rows_content = ""
        for i, (time_str, val) in enumerate(day_data):
            hour = int(time_str.split(':')[0])
            icon = get_weather_icon(float(val.get('cloud',0) or 0), float(val.get('precip',0) or 0), hour, date_str, lat, lon)
            
            temp = float(val.get('temp',0) or 0)
            temp_bar = create_smooth_bar_segment(i, day_data, 'temp', -10, 35, ('temp',))
            
            wind_s = float(val.get('wind_s',0) or 0)
            wind_g = float(val.get('wind_g',0) or 0)
            # Logic: Input 0 (N) -> Output 180 (Down)
            # Input 90 (E) -> Output 270 (Left)
            # Input 180 (S) -> Output 0 (Up)
            # Input 270 (W) -> Output 90 (Right)
            wind_d = (float(val.get('wind_d',0) or 0) + 180) % 360
            
            wave_h = float(val.get('wave_h',0) or 0)
            wave_bar = create_smooth_bar_segment(i, day_data, 'wave_h', 0, 4, '#22d3ee')
            wave_d = (float(val.get('wave_d',0) or 0) + 180) % 360
            
            o_temp = float(val.get('o_temp',0) or 0)
            o_temp_bar = create_smooth_bar_segment(i, day_data, 'o_temp', 0, 30, ('otemp',))
            
            s_color = "#00ff00" if wind_s >= 4 else "var(--water-cyan)"
            
            rows_content += f"""
            <tr>
                <td class="col-time">{time_str[:2]}</td>
                <td class="col-icon">{icon}</td>
                <td class="col-val">{temp:.1f}</td>
                <td class="col-bar-cell">{temp_bar}</td>
                <td class="col-wind-txt"><span class="g">{wind_g:.1f}</span><span class="s" style="color: {s_color}">{wind_s:.1f}</span></td>
                <td class="col-wind-dir"><span class="arrow" style="display:inline-block; transform: rotate({wind_d}deg)">↑</span></td>
                <td class="col-val">{wave_h:.1f}</td>
                <td class="col-bar-cell">{wave_bar}</td>
                <td class="col-wave-dir"><span class="arrow" style="display:inline-block; transform: rotate({wave_d}deg)">↑</span></td>
                <td class="col-bar-cell" style="width:40px">{o_temp_bar}<span class="val-overlay">{o_temp:.1f}</span></td>
            </tr>
            """

        cards_html += f"""
        <div class="day-card" style="animation-delay: {d_idx * 0.05}s">
            <div class="card-header-row">
                <div class="date-title">{date_str[5:]}</div>
            </div>
            
            <div class="card-chart-area">
                {chart_svg}
            </div>

            <div class="card-table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>天气</th>
                            <th>温度(°C)</th>
                            <th style="width:40px"></th>
                            <th>阵风/风速(m/s)</th>
                            <th>风向</th>
                            <th>浪高(m)</th>
                            <th style="width:40px"></th>
                            <th>浪向</th>
                            <th style="width:40px">水温</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_content}
                    </tbody>
                </table>
            </div>
        </div>
        """
    return cards_html

def generate_html(weather_data, location_name, location_data):
    
    output_path = location_data["EN_name"] + ".html"


        
    lat = float(location_data.get('latitude', 39.9))
    lon = float(location_data.get('longitude', 116.4))
    
    loc_info_html = location_name
    if location_data.get('city'):
        loc_info_html += f" <span class='loc-sub'>({location_data['city']} {location_data['latitude']}, {location_data['longitude']})</span>"

    dashboard_html = generate_dashboard_content(weather_data, lat, lon)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Wind-Chaser-Club - 风浪矩阵</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-deep: #020617;
            --card-bg: #1e293b;
            --sunshine: #fbbf24;
            --energy-orange: #f97316;
            --water-cyan: #22d3ee;
            --text-bright: #f8fafc;
            --text-dim: #94a3b8;
            --border-soft: rgba(255, 255, 255, 0.05);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            background: #070c1d;
            background-image: radial-gradient(circle at 50% -20%, #1e293b 0%, #070c1d 80%);
            color: var(--text-bright); 
            font-family: 'Outfit', sans-serif;
            padding: 5px;
            overflow-x: hidden;
            min-height: 100vh;
        }}
        header {{ margin: 10px 0 15px 0; text-align: center; }}
        .loc-details {{ font-size: 1rem; font-weight: 700; color: #ffffff; letter-spacing: 1px; }}
        .loc-sub {{ opacity: 0.6; font-size: 0.8rem; color: var(--text-dim); }}

        .cards-container {{
            display: flex;
            gap: 12px;
            overflow-x: auto;
            padding: 5px 2px 20px 2px;
            scroll-snap-type: x mandatory;
            scrollbar-width: none;
        }}
        .cards-container::-webkit-scrollbar {{ display: none; }}
        
        .day-card {{
            flex: 0 0 94vw;
            max-width: 420px;
            background: var(--card-bg);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 16px;
            padding: 12px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-soft);
            scroll-snap-align: center;
            animation: fadeInUp 0.4s ease-out forwards;
            opacity: 0;
            display: flex; flex-direction: column;
            height: fit-content;
        }}

        .card-header-row {{ display: flex; justify-content: flex-start; margin-bottom: 8px; }}
        .date-title {{ font-size: 0.95rem; font-weight: 700; color: var(--sunshine); }}

        .card-table-wrapper {{ overflow: hidden; }}
        .data-table {{ width: 100%; border-collapse: collapse; border-spacing: 0; }}
        .data-table th {{
            background: rgba(15, 23, 42, 0.5);
            padding: 5px 2px; color: var(--text-dim); font-size: 0.6rem; text-transform: uppercase;
            border-bottom: 1px solid var(--border-soft);
        }}
        .data-table td {{ padding: 0; height: 26px; text-align: center; }}
        .data-table tr:nth-child(even) {{ background: rgba(15, 23, 42, 0.4); }}
        
        .col-time {{ font-family: 'JetBrains Mono'; font-size: 0.75rem; color: var(--text-dim); font-weight: 600; }}
        .col-icon {{ font-size: 1rem; }}
        .col-val {{ font-weight: 700; font-size: 0.8rem; padding: 0 4px !important; }}
        .col-wind-txt .g {{ color: var(--energy-orange); font-size: 0.55rem; }}
        .col-wind-txt .s {{ color: var(--water-cyan); font-size: 0.75rem; font-weight: 700; }}
        .arrow {{ font-size: 0.8rem; opacity: 0.7; }}

        /* Connected Vertical Area Bars */
        .col-bar-cell {{ width: 40px; position: relative; padding: 0 !important; }}
        .smooth-bar-container {{ width: 100%; height: 26px; position: relative; }}
        .smooth-bar-container svg {{ width: 100%; height: 100%; display: block; }}
        
        .card-chart-area {{
            padding: 5px 10px 10px 0px;
            margin-bottom: 10px;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 8px;
        }}
        .wind-main-chart {{ width: 100%; height: 90px; overflow: visible; display: block; }}
        .chart-label {{ fill: #cbd5e1; font-size: 8px; font-family: 'JetBrains Mono'; font-weight: 500; opacity: 0.8; }}
        .chart-label-y {{ fill: #94a3b8; font-size: 8px; font-family: 'JetBrains Mono'; font-weight: 600; opacity: 0.6; }}

        /* Chart Animations */
        .animate-path {{
            stroke-dasharray: 2000;
            stroke-dashoffset: 2000;
            animation: drawPath 2s ease-out forwards;
            animation-delay: 0.5s;
        }}
        .animate-area {{
            opacity: 0;
            animation: fadeInArea 1s ease-out forwards;
            animation-delay: 1.5s;
        }}

        @keyframes drawPath {{
            to {{ stroke-dashoffset: 0; }}
        }}
        @keyframes fadeInArea {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .val-overlay {{ 
            position: absolute; width: 100%; text-align: center; top: 50%; left: 0; 
            transform: translateY(-50%); font-size: 0.55rem; font-weight: 800; z-index: 2;
            color: rgba(255,255,255,0.9);
            text-shadow: 0 0 3px rgba(0,0,0,0.5);
        }}

        @media (min-width: 1000px) {{
            .day-card {{ flex: 0 0 380px; }}
            .cards-container {{ justify-content: center; }}
        }}
        .footer {{ 
            text-align: center; margin-top: 20px; margin-bottom: 20px; 
            font-size: 11px; color: #64748b; opacity: 0.8; letter-spacing: 1px;
        }}
    </style>
</head>
<body>
    <header>
        <div class="loc-details">{loc_info_html}</div>
    </header>

    <div class="cards-container">
        {dashboard_html}
    </div>
    <div class="footer">
        Copyright©2026 Wind-Chaser-Club {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Success: {output_path} generated.")

if __name__ == "__main__":
    with open('weather_data.json', 'r', encoding='utf-8') as f:
        all_weather_data = json.load(f)

    with open('location.json', 'r', encoding='utf-8') as f:
        location_data = json.load(f)

    location_name = "蔚蓝海岸"
    weather_data = all_weather_data[location_name]
    generate_html(weather_data, location_name, location_data["蔚蓝海岸"])

