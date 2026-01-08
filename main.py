print("--- 脚本启动：正在加载库 ---", flush=True)
import time
import requests
import json
from renderindex import render_index
from render_html import generate_html
print("--- 库加载完成 ---", flush=True)


# 1. 基础配置
#LAT = 39.895595
#LON = 119.551064
#DAYS = 7

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
    

def get_data(single_location_config,name):    # 获取数据
    
    LAT = single_location_config['latitude'] # 纬度
    LON = single_location_config['longitude'] # 经度
    #print(LAT, LON, name)
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
            f"&hourly=temperature_2m,cloudcover,precipitation,windspeed_10m,winddirection_10m,windgusts_10m"
            f"&forecast_days=7&wind_speed_unit=ms&timezone=auto"
        ) # 天气预报API

    marine_url = (
            f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}"
            f"&hourly=swell_wave_height,swell_wave_direction,sea_surface_temperature"
            f"&forecast_days=7&timezone=auto"
        ) # 海洋预报API
    
    weather_data = {} # 存储天气数据
    retries = 3
    attempt = 0
    while attempt < retries:
        try:
            print(f"{name}尝试第 {attempt + 1} 次请求...")
            # 请求气象和海洋数据
            w_res = requests.get(weather_url,timeout=30).json()
            m_res = requests.get(marine_url,timeout=30).json()   
            
            
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
                
            return weather_data

        except Exception as e:
            attempt += 1
            print(f"发生错误: {e}")
            if attempt < retries:
                print("准备重试...")
                time.sleep(2)  # 等待一会儿再试
            else:
                print("达到最大重试次数，放弃。")
                return None   

    

if __name__ == "__main__":
    print('--- 脚本启动', flush=True)
    with open("location.json", "r") as f: # 读取 location.json 文件
        location_data = json.load(f)
    print('location读取成功')
    result = {}
    print('weather_data初始化成功')

    for i in location_data: # 遍历 location.json 文件中的每个位置
        print(f"请求 {i} 数据")  
        data = get_data(location_data[i],i)  
        result[i] = data
        print(f"{i}数据已保存")

        generate_html(data,i,location_data[i])

    render_index(result,location_data)
    #with open("weather_data.json", "w") as f: # 将数据保存到 weather_data.json 文件中
    #    json.dump(weather_data, f, indent=4)

    #print(weather_data)
