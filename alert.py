#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山西东风南方汽车销售服务有限公司 - 天气预警机器人
【临时测试版】强制执行预报推送，用于调试抓取问题
"""

import requests
import json
import os
import re
from datetime import datetime, timedelta
from lxml import etree

# ======================== 配置区域 ========================
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"

ALERT_API_URL = "https://weather.cma.cn/api/map/alarm?adcode=14"

CITY_FORECAST_URLS = {
    "太原": "http://www.nmc.cn/publish/forecast/ASX/taiyuan.html",
    "大同": "http://www.nmc.cn/publish/forecast/ASX/datong.html",
    "朔州": "http://www.nmc.cn/publish/forecast/ASX/shuozhou.html",
    "忻州": "http://www.nmc.cn/publish/forecast/ASX/xinzhou.html",
    "吕梁": "http://www.nmc.cn/publish/forecast/ASX/lvliang.html",
    "晋中": "http://www.nmc.cn/publish/forecast/ASX/jinzhong.html",
    "阳泉": "http://www.nmc.cn/publish/forecast/ASX/yangquan.html",
    "长治": "http://www.nmc.cn/publish/forecast/ASX/changzhi.html",
    "晋城": "http://www.nmc.cn/publish/forecast/ASX/jincheng.html",
    "临汾": "http://www.nmc.cn/publish/forecast/ASX/linfen.html",
    "运城": "http://www.nmc.cn/publish/forecast/ASX/yuncheng.html"
}

FORECAST_KEYWORDS = [
    "中雨", "大雨", "暴雨", "大暴雨",
    "中雪", "大雪", "暴雪",
    "大风", "雷暴大风", "冰雹",
    "高温", "雷电", "雷阵雨"
]

COUNTY_TO_CITY = {
    "太原": "太原", "小店": "太原", "迎泽": "太原", "杏花岭": "太原", "尖草坪": "太原",
    "万柏林": "太原", "晋源": "太原", "清徐": "太原", "阳曲": "太原", "娄烦": "太原", "古交": "太原",
    "大同": "大同", "平城": "大同", "云冈": "大同", "云州": "大同", "新荣": "大同",
    "阳高": "大同", "天镇": "大同", "广灵": "大同", "灵丘": "大同", "浑源": "大同", "左云": "大同",
    "朔州": "朔州", "朔城": "朔州", "平鲁": "朔州", "山阴": "朔州", "应县": "朔州", "右玉": "朔州", "怀仁": "朔州",
    "忻州": "忻州", "忻府": "忻州", "定襄": "忻州", "五台": "忻州", "代县": "忻州", "繁峙": "忻州",
    "宁武": "忻州", "静乐": "忻州", "神池": "忻州", "五寨": "忻州", "岢岚": "忻州", "河曲": "忻州",
    "保德": "忻州", "偏关": "忻州", "原平": "忻州",
    "吕梁": "吕梁", "离石": "吕梁", "文水": "吕梁", "交城": "吕梁", "兴县": "吕梁", "临县": "吕梁",
    "柳林": "吕梁", "石楼": "吕梁", "岚县": "吕梁", "方山": "吕梁", "中阳": "吕梁", "交口": "吕梁",
    "孝义": "吕梁", "汾阳": "吕梁",
    "晋中": "晋中", "榆次": "晋中", "太谷": "晋中", "祁县": "晋中", "平遥": "晋中", "灵石": "晋中",
    "介休": "晋中", "榆社": "晋中", "左权": "晋中", "和顺": "晋中", "昔阳": "晋中", "寿阳": "晋中",
    "阳泉": "阳泉", "城区": "阳泉", "矿区": "阳泉", "郊区": "阳泉", "平定": "阳泉", "盂县": "阳泉",
    "长治": "长治", "潞州": "长治", "上党": "长治", "屯留": "长治", "潞城": "长治",
    "襄垣": "长治", "平顺": "长治", "黎城": "长治", "壶关": "长治", "长子": "长治", "武乡": "长治", "沁县": "长治", "沁源": "长治",
    "晋城": "晋城", "城区": "晋城", "沁水": "晋城", "阳城": "晋城", "陵川": "晋城", "泽州": "晋城", "高平": "晋城",
    "临汾": "临汾", "尧都": "临汾", "曲沃": "临汾", "翼城": "临汾", "襄汾": "临汾", "洪洞": "临汾",
    "古县": "临汾", "安泽": "临汾", "浮山": "临汾", "吉县": "临汾", "乡宁": "临汾", "大宁": "临汾",
    "隰县": "临汾", "永和": "临汾", "蒲县": "临汾", "汾西": "临汾", "侯马": "临汾", "霍州": "临汾",
    "运城": "运城", "盐湖": "运城", "临猗": "运城", "万荣": "运城", "闻喜": "运城", "稷山": "运城",
    "新绛": "运城", "绛县": "运城", "垣曲": "运城", "夏县": "运城", "平陆": "运城", "芮城": "运城",
    "永济": "运城", "河津": "运城"
}

FORECAST_CACHE_FILE = "forecast_sent_date.txt"
ALERT_CACHE_FILE = "alert_cache.json"

def is_beijing_time_between(start_hour, end_hour):
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    return start_hour <= now_bj.hour < end_hour

def get_current_beijing_date():
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    return now_bj.strftime("%Y-%m-%d")

def send_to_wecom(content):
    if not WEBHOOK_URL:
        print("错误：未设置 WEBHOOK_URL")
        return False
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "text", "text": {"content": content}}
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            print("消息发送成功")
            return True
        else:
            print(f"消息发送失败，状态码：{resp.status_code}")
            return False
    except Exception as e:
        print(f"消息发送异常：{e}")
        return False

def get_city_forecast(city_name, url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        tree = etree.HTML(resp.text)
        day_divs = tree.xpath('//*[@id="day7"]/div[position()<=3]')
        full_text = ""
        for div in day_divs:
            text = "".join(div.itertext())
            full_text += text + " "
        
        print(f"[DEBUG] {city_name} 抓取文本预览: {full_text[:500]}...")
        
        found = [kw for kw in FORECAST_KEYWORDS if kw in full_text]
        return list(set(found))
    except Exception as e:
        print(f"获取 {city_name} 预报失败：{e}")
        return None

def get_province_forecast():
    result = {}
    any_success = False
    for city, url in CITY_FORECAST_URLS.items():
        keywords = get_city_forecast(city, url)
        if keywords is None:
            continue
        any_success = True
        if keywords:
            result[city] = keywords
            print(f"[DEBUG] {city} 匹配到关键词: {keywords}")
        else:
            print(f"[DEBUG] {city} 未匹配到任何关键词")
    return result, any_success

def build_forecast_message(forecast_data):
    if not forecast_data:
        return None
    lines = ["【山西未来三天灾害天气提醒】"]
    for city, keywords in forecast_data.items():
        unique_kws = sorted(set(keywords))
        lines.append(f"{city}：{', '.join(unique_kws)}")
    lines.append("\n⚠️ 请各单位提前做好车辆防护、排水检查、广告牌加固、防暑降温等工作。")
    return "\n".join(lines)

def has_forecast_sent_today():
    if not os.path.exists(FORECAST_CACHE_FILE):
        return False
    with open(FORECAST_CACHE_FILE, "r", encoding="utf-8") as f:
        saved_date = f.read().strip()
    return saved_date == get_current_beijing_date()

def mark_forecast_sent():
    with open(FORECAST_CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(get_current_beijing_date())

def run_daily_forecast():
    # 临时测试：忽略今日是否已发送，强制运行
    # if has_forecast_sent_today():
    #     print("今日预报已发送过，跳过")
    #     return
    print("开始获取全省未来三天预报...")
    forecast, any_success = get_province_forecast()
    
    if not any_success:
        print("所有城市预报抓取失败，本次不推送")
        return
    
    if not forecast:
        print("未检测到需要关注的灾害天气")
        return
    
    msg = build_forecast_message(forecast)
    if msg:
        send_to_wecom(msg)
        # 临时测试：不标记已发送，以便多次测试
        # mark_forecast_sent()
    else:
        print("预报消息为空，不推送")

def fetch_alerts():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(ALERT_API_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            print(f"预警接口返回错误码：{data.get('code')}")
            return []
        alerts = data.get("data", [])
        result = []
        for alert in alerts:
            title = alert.get("headline", "")
            level_match = re.search(r'(蓝色|黄色|橙色|红色)预警', title)
            if not level_match:
                continue
            level = level_match.group(1)
            type_match = re.search(r'([\u4e00-\u9fa5]+)(?:蓝色|黄色|橙色|红色)预警', title)
            alert_type = type_match.group(1) if type_match else "未知"
            location = alert.get("location", "")
            pub_time = alert.get("effective", "")
            result.append({
                "type": alert_type,
                "level": level,
                "location": location,
                "pub_time": pub_time
            })
        return result
    except Exception as e:
        print(f"获取预警失败：{e}")
        return []

def convert_locations_to_cities(locations):
    cities = set()
    for loc in locations:
        for county, city in COUNTY_TO_CITY.items():
            if county in loc:
                cities.add(city)
                break
    valid_cities = [c for c in cities if c in CITY_FORECAST_URLS]
    return sorted(valid_cities)

def group_alerts_by_type_level(alerts):
    groups = {}
    for alert in alerts:
        key = (alert["type"], alert["level"])
        if key not in groups:
            groups[key] = {
                "type": alert["type"],
                "level": alert["level"],
                "locations": [],
                "pub_time": alert["pub_time"]
            }
        groups[key]["locations"].append(alert["location"])
    result = []
    for key, group in groups.items():
        cities = convert_locations_to_cities(group["locations"])
        if not cities:
            continue
        result.append({
            "type": group["type"],
            "level": group["level"],
            "cities": cities,
            "pub_time": group["pub_time"]
        })
    return result

def get_alert_signature(alert):
    cities_str = ",".join(sorted(alert["cities"]))
    return f"{alert['type']}_{cities_str}"

def load_alert_cache():
    if not os.path.exists(ALERT_CACHE_FILE):
        return {"date": "", "signatures": []}
    try:
        with open(ALERT_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != get_current_beijing_date():
            return {"date": "", "signatures": []}
        return data
    except:
        return {"date": "", "signatures": []}

def save_alert_cache(signatures):
    data = {
        "date": get_current_beijing_date(),
        "signatures": signatures
    }
    with open(ALERT_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_prevention_tips(alert_type, level):
    base = "请各单位"
    if "暴雨" in alert_type:
        if level in ["橙色", "红色"]:
            return base + "立即将露天展车转移至室内，无法转移的用防雨布遮盖；检查排水系统；暂停户外试驾。"
        else:
            return base + "提前转移低洼处车辆，清理排水口，注意观察雨势变化。"
    elif "大风" in alert_type or "雷暴大风" in alert_type:
        if level in ["橙色", "红色"]:
            return base + "立即加固户外广告牌、易拉宝；停止户外作业；车辆停放远离大树和建筑边缘。"
        else:
            return base + "检查户外设施稳固情况，提醒员工注意高空坠物。"
    elif "冰雹" in alert_type:
        return base + "立即将所有露天车辆转移至室内或覆盖防雹车衣；人员进入室内躲避。"
    elif "雪" in alert_type:
        if "暴雪" in alert_type or "大雪" in alert_type:
            return base + "检查屋顶承重，及时清理积雪；准备除雪工具；提醒员工行车安全。"
        else:
            return base + "注意路面湿滑，减少户外活动。"
    elif "高温" in alert_type:
        return base + "注意展厅空调提前开启，准备防暑药品；检查车辆电瓶和轮胎，避免自燃。"
    elif "雷电" in alert_type:
        return base + "暂停户外试驾和作业；关闭不必要的电器；人员进入室内，远离金属门窗。"
    else:
        return base + "关注天气变化，做好相应防范措施。"

def build_alert_message(alert):
    level_text = alert["level"]
    cities_text = "、".join(alert["cities"])
    tip = get_prevention_tips(alert["type"], alert["level"])
    msg = f"""【山西气象预警】
{alert['type']}{level_text}预警：{cities_text}
（发布时间：{alert['pub_time']}）
{tip}"""
    return msg

def run_alert_check():
    print("开始检查气象预警...")
    alerts = fetch_alerts()
    if not alerts:
        print("未获取到任何预警")
        return
    
    grouped = group_alerts_by_type_level(alerts)
    print(f"获取到 {len(grouped)} 个有效预警组")
    
    cache = load_alert_cache()
    sent_signatures = set(cache["signatures"])
    
    new_alerts = []
    for alert in grouped:
        sig = get_alert_signature(alert)
        if sig not in sent_signatures:
            new_alerts.append(alert)
            sent_signatures.add(sig)
        else:
            print(f"跳过已发送预警类型：{alert['type']} 影响城市 {alert['cities']} (等级 {alert['level']} 变化或范围扩大均不重复发送)")
    
    if not new_alerts:
        print("没有需要推送的新预警")
        return
    
    for alert in new_alerts:
        msg = build_alert_message(alert)
        send_to_wecom(msg)
    
    save_alert_cache(list(sent_signatures))
    print(f"已推送 {len(new_alerts)} 条新预警")

if __name__ == "__main__":
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    current_hour = now_bj.hour
    
    print(f"当前北京时间: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 临时测试：强制运行预报推送（忽略时间）
    print("===== 临时测试：强制执行每日预报推送 =====")
    run_daily_forecast()
    
    # 如果也在8-21点之间，继续预警检查
    if is_beijing_time_between(8, 21):
        print("===== 执行预警检查 =====")
        run_alert_check()
    else:
        print("当前不在8-21点，跳过预警检查")
