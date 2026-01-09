import json
from jinja2 import Template
from collections import Counter

def render_index(data, location_data):
    processed_data = []

    for location, timeline in data.items():
        # 确保时间点排序
        sorted_hours = sorted(timeline.keys())[:120]
        total_steps = len(sorted_hours)
        
        # 统计每天出现的次数，用于计算居中偏移
        date_keys = [ts.split(' ')[0] for ts in sorted_hours]
        day_counts = Counter(date_keys)
        
        hourly_colors = []
        line_stops = [] 
        days_labels = []
        last_day = ""
        
        for i, ts in enumerate(sorted_hours):
            # 颜色平滑渐变逻辑
            wind_s = timeline[ts].get('wind_s', 0)
            hue = max(0, 220 - int(wind_s * 15)) 
            hourly_colors.append(f"hsl({hue}, 80%, 50%)")
            
            # 日期标签与分隔线逻辑
            day_full_str = ts.split(' ')[0]
            current_day = day_full_str.split('-')[-1] + "日"
            
            if current_day != last_day:
                pos = (i / total_steps) * 100
                
                # 分隔线
                if i > 0:
                    line_stops.append(f"transparent calc({pos}% - 2px)")
                    line_stops.append(f"rgba(51,65,85,0.3) {pos}%")
                    line_stops.append(f"transparent calc({pos}% + 2px)")
                
                # 居中日期标签
                this_day_count = day_counts[day_full_str]
                center_pos = ((i + (this_day_count / 2)) / total_steps) * 100
                days_labels.append({"label": current_day, "pos": center_pos})
                
                last_day = current_day

        # 提取城市信息
        current_loc_info = location_data.get(location, {})
        city_info = current_loc_info.get("city", "未知")
        location_title = f"{location} ({city_info})"
        
        # 提取 linkname (增加安全处理，防止 Key 不存在)
        en_name = current_loc_info.get('EN_name', 'default')
        linkname = en_name + '.html'

        processed_data.append({
            "location": location_title,
            "color_str": ", ".join(hourly_colors),
            "separator_gradient": f"linear-gradient(to right, {', '.join(line_stops)})" if line_stops else "none",
            "labels": days_labels,
            "linkname": linkname
        })

    # 2. HTML 模板 (加入链接逻辑)
    html_template = """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background-color: #070e2d; color: #f1f5f9; font-family: sans-serif; margin: 0; padding: 10px; }
            .main-card { 
                max-width: 800px; margin: 10px auto; background: #1e293b; 
                border-radius: 16px; border: 1px solid #334155;
                padding: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            }
            .header { text-align: center; margin-bottom: 10px; margin-top: 6px; }
            .header h2 { margin: 0; font-size: 26px; color: #fff; letter-spacing: 1px; }
            .header h3 { margin: 8px 0 0; font-size: 13px; color: #94a3b8; font-weight: normal; text-transform: uppercase; letter-spacing: 2px; }

            .location-item { margin-bottom: 8px; }
            
            /* 链接样式重置 */
            .loc-link { text-decoration: none; display: block; color: inherit; transition: opacity 0.2s; }
            .loc-link:hover { opacity: 0.8; }
            .loc-link:hover .heatmap-wrap { transform: scaleY(1.1); }

            .loc-title { font-size: 15px; margin-bottom: 8px; color: #fbbf24; font-weight: bold; }
            
            .heatmap-wrap { 
                position: relative; width: 100%; height: 12px; 
                border-radius: 6px; overflow: hidden; background: #000;
                transition: transform 0.2s; /* 增加平滑缩放效果 */
            }
            
            .layer-colors { 
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                z-index: 1;
            }
            
            .layer-lines { 
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                z-index: 2; pointer-events: none;
            }

            .axis { position: relative; width: 100%; height: 10px; margin-top: 10px; }
            .tick { position: absolute; font-size: 11px; color: #8b949e; transform: translateX(-50%); }

            @media (max-width: 600px) {
                .main-card { padding: 15px; }
                .heatmap-wrap { height: 12px; }
            }
            .footer { 
                text-align: center; margin-top: 40px; margin-bottom: 20px; 
                font-size: 11px; color: #64748b; opacity: 0.8; letter-spacing: 1px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>追风区域导航</h2>
            <h3>Open-Meteo Data Service</h3>
        </div>
        <div class="main-card">
            {% for loc in data %}
            <div class="location-item">
                <a href="{{ loc.linkname }}" class="loc-link">
                    <div class="loc-title">{{ loc.location }}</div>
                    <div class="heatmap-wrap">
                        <div class="layer-colors" style="background: linear-gradient(to right, {{ loc.color_str }});"></div>
                        <div class="layer-lines" style="background: {{ loc.separator_gradient }};"></div>
                    </div>
                </a>
                <div class="axis">
                    {% for label in loc.labels %}
                    <div class="tick" style="left: {{ label.pos }}%;">{{ label.label }}</div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="footer">
            Copyright©2026 Wind-Chaser-Club
        </div>
    </body>
    </html>
    """

    template = Template(html_template)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data=processed_data))

    print("渲染完成:index.html")

if __name__ == "__main__":
    # 1. 加载数据
    with open('weather_data.json', 'r', encoding='utf-8') as f:
        weather_data = json.load(f)

    try:
        with open('location.json', 'r', encoding='utf-8') as f:
            location_data = json.load(f)
    except FileNotFoundError:
        location_data = {}
    render_index(weather_data, location_data)

        

