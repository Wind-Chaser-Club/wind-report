import requests
import json
from datetime import datetime
from renderindex import render_index
from render_html import generate_html



# 1. 基础配置
#LAT = 39.895595
#LON = 119.551064
DAYS = 7

# 2. 构建气象 API URL (云量、雨量、气温、风速、风向、阵风)
#weather_url = (
#    f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
#    f"&hourly=temperature_2m,cloudcover,precipitation,windspeed_10m,winddirection_10m,windgusts_10m"
#    f"&forecast_days={DAYS}&wind_speed_unit=ms&timezone=auto"
#)

# 3. 构建海洋 API URL (海浪高度、方向、海水表层温度)
#marine_url = (
#    f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}"
#    f"&hourly=swell_wave_height,swell_wave_direction,sea_surface_temperature"
#    f"&forecast_days={DAYS}&timezone=auto"
#)   
    

def get_data(location_data,name):    # 获取数据
    
    LAT = location_data['latitude'] # 纬度
    LON = location_data['longitude'] # 经度
    #print(LAT, LON, name)
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
            f"&hourly=temperature_2m,cloudcover,precipitation,windspeed_10m,winddirection_10m,windgusts_10m"
            f"&forecast_days={DAYS}&wind_speed_unit=ms&timezone=auto"
        ) # 天气预报API

    marine_url = (
            f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}"
            f"&hourly=swell_wave_height,swell_wave_direction,sea_surface_temperature"
            f"&forecast_days={DAYS}&timezone=auto"
        ) # 海洋预报API
    
    try:
        # 请求气象和海洋数据
        w_res = requests.get(weather_url).json()
        m_res = requests.get(marine_url).json()
        
        weather_data = {} # 存储天气数据
                

        #print(f"--- 坐标 ({LAT}, {LON}) 未来 7 天预报 ---")
        #print(f"{'时间':<16} | {'云量%':<4} | {'雨量mm':<4} |{'气温C°':<6}| {'海水温度C°':<12}| {'风速/阵风(m/s)':<10}| {'风向':<4}| {'浪高(m)':<5} | {'涌浪方向':<5}")
        #print("-" * 85)

        # 遍历每小时的数据 
        for i in range(0, len(w_res['hourly']['time'])):
            time_str = w_res['hourly']['time'][i].replace("T", " ")
            cloud = w_res['hourly']['cloudcover'][i]
            precip = w_res['hourly']['precipitation'][i]
            temp = w_res['hourly']['temperature_2m'][i]
            wind_s = w_res['hourly']['windspeed_10m'][i]
            wind_g = w_res['hourly']['windgusts_10m'][i]
            wind_d = w_res['hourly']['winddirection_10m'][i]
            
            # 海浪数据可能在某些时刻为 null (例如离岸太近或无数据)
            wave_h = m_res['hourly']['swell_wave_height'][i]
            wave_d = m_res['hourly']['swell_wave_direction'][i]
            o_temp = m_res['hourly']['sea_surface_temperature'][i]
            wave_h_str = f"{wave_h}" if wave_h is not None else "N/A"
            wave_d_str = f"{wave_d}" if wave_d is not None else "N/A"

            weather_data[time_str] = {
                "cloud": cloud,
                "precip": precip,
                "temp": temp,
                "wind_s": wind_s,
                "wind_g": wind_g,
                "wind_d": wind_d,
                "wave_h": wave_h_str,
                "wave_d": wave_d_str,
                "o_temp": o_temp
            }

            #print(f"{time_str:<18} | {cloud:<6} | {precip:<6} | {temp:<6} | {o_temp:<14} | {wind_s:<6}/{wind_g:<6} | {wind_d:<4}° | {wave_h_str:<5} | {wave_d_str:<5}")

    except Exception as e:
        print(f"获取数据失败: {e}")
    
    

    return weather_data


def render_data():
    with open("weather_data.json", "r") as f: # 读取 weather_data.json 文件
        weather_data = json.load(f)
        print(type(weather_data), weather_data)


if __name__ == "__main__":
    with open("location.json", "r") as f: # 读取 location.json 文件
        location_data = json.load(f)
        #print(type(location_data), location_data)
    
    weather_data = {}
        

    for i in location_data: # 遍历 location.json 文件中的每个位置
        #print(location_data[i])  
        data = get_data(location_data[i],i)  
        weather_data[i] = data
        print(f"{i}数据已保存")

        generate_html(data,i,location_data[i])

    render_index(weather_data,location_data)
    with open("weather_data.json", "w") as f: # 将数据保存到 weather_data.json 文件中
        json.dump(weather_data, f, indent=4)
    #print(weather_data)