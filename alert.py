#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山西东风南方汽车销售服务有限公司 - 天气预警机器人
最终稳定版
"""

import requests
import json
import os
import re
from datetime import datetime, timedelta
from lxml import etree

# ======================== 配置 ========================
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"
ALERT_API_URL = "https://weather.cma.cn/api/map/alarm?adcode=14"

ALL_CITIES = ["太原", "大同", "朔州", "忻州", "吕梁", "晋中", "阳泉", "长治", "晋城", "临汾", "运城"]
ALERT_TARGET_CITIES = ["太原", "晋中", "吕梁", "阳泉", "忻州", "长治", "运城"]
IGNORE_ALERT_TYPES = ["高温", "雷电"]

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
    "柳林": "吕梁", "石楼": "吕梁", "岚": "吕梁", "方山": "吕梁", "中阳": "吕梁", "交口": "吕梁",
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

# ======================== 辅助函数 ========================
def is_beijing_time_between(start_hour, end_hour):
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    return start_hour <= now_bj.hour < end_hour

def get_current_beijing_date():
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    return now_bj.strftime("%Y-%m-%d")

def get_weekday():
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    now_bj = datetime.utcnow() + timedelta(hours=8)
    return weekdays[now_bj.weekday()]

def send_to_wecom(content):
    if not WEBHOOK_URL:
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

# ======================== 天气预报 ========================
def get_city_today_weather(city_name, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        tree = etree.HTML(resp.text)
        today_div = tree.xpath('//*[@id="day7"]/div[1]')
        if not today_div:
            return None
        div = today_div[0]
        weather_ele = div.xpath('.//p[@class="wea"]/text()')
        weather = weather_ele[0].strip() if weather_ele else ""
        temp_ele = div.xpath('.//p[@class="tem"]/span/text()')
        if len(temp_ele) >= 2:
            temp_str = f"{temp_ele[1].strip()}~{temp_ele[0].strip()}℃"
        elif len(temp_ele) == 1:
            temp_str = f"{temp_ele[0].strip()}℃"
        else:
            full_text = "".join(div.itertext())
            temps = re.findall(r'(\d+)℃', full_text)
            if temps:
                temp_str = f"{temps[-1]}~{temps[0]}℃" if len(temps)>=2 else f"{temps[0]}℃"
            else:
                temp_str = "?"
        wind_ele = div.xpath('.//p[@class="win"]/text()')
        wind = wind_ele[0].strip() if wind_ele else ""
        return f"{weather}，气温{temp_str}，{wind}"
    except Exception as e:
        print(f"获取 {city_name} 天气失败：{e}")
        return None

def get_all_cities_weather():
    result = {}
    any_success = False
    for city in ALL_CITIES:
        url = CITY_FORECAST_URLS.get(city)
        if not url:
            continue
        detail = get_city_today_weather(city, url)
        if detail is None:
            continue
        any_success = True
        result[city] = detail
    return result, any_success

def build_today_forecast_message(weather_data):
    if not weather_data:
        return None
    today = get_current_beijing_date()
    weekday = get_weekday()
    lines = [f"【山西省天气预报】{today}（{weekday}） 发布", ""]
    for city in ALL_CITIES:
        if city in weather_data:
            lines.append(f"📍 {city}：{weather_data[city]}；")
    if len(lines) > 2:
        lines[-1] = lines[-1].rstrip("；") + "。"
    lines.append("")
    lines.append("⚠️ 温馨提示：请各单位关注实时气象预警，做好车辆防护、排水检查等应急工作；提醒员工及合作单位做好人员及财产安全防护。")
    lines.append("📢 数据来源：中央气象台")
    return "\n".join(lines)

def has_forecast_sent_today():
    if not os.path.exists(FORECAST_CACHE_FILE):
        return False
    with open(FORECAST_CACHE_FILE, "r") as f:
        return f.read().strip() == get_current_beijing_date()

def mark_forecast_sent():
    with open(FORECAST_CACHE_FILE, "w") as f:
        f.write(get_current_beijing_date())

def run_daily_forecast():
    if has_forecast_sent_today():
        print("今日天气预报已发送过，跳过")
        return
    print("开始获取全省当天天气预报...")
    weather, any_success = get_all_cities_weather()
    if not any_success:
        print("所有城市天气获取失败，本次不推送")
        return
    if not weather:
        print("未获取到天气数据，标记已发送")
        mark_forecast_sent()
        return
    msg = build_today_forecast_message(weather)
    if msg:
        send_to_wecom(msg)
        mark_forecast_sent()
    else:
        print("消息为空")

# ======================== 预警处理（核心修复） ========================
def extract_city_from_title(title):
    """
    提取预警中的区县名或地级市名。
    优先提取“县”前的部分，找到最近的“市”或“省”作为起始。
    如果没有“县”，则提取“市”前的部分（地级市）。
    """
    # 查找“县”
    idx = title.find('县')
    if idx != -1:
        # 向前找最近的“市”或“省”
        start = idx
        for i in range(idx-1, -1, -1):
            if title[i] in ('市', '省'):
                start = i+1
                break
        if start < idx:
            return title[start:idx]
    # 没有县，查找“市”（地级市直接发布）
    idx = title.find('市')
    if idx != -1:
        start = idx
        for i in range(idx-1, -1, -1):
            if title[i] in ('省', '市'):
                start = i+1
                break
        if start < idx:
            return title[start:idx]
    return None

def city_to_target(city_name):
    """将提取的城市名转换为目标地级市（若在映射表中则转换，否则视为地级市本身）"""
    if not city_name:
        return None
    if city_name in COUNTY_TO_CITY:
        return COUNTY_TO_CITY[city_name]
    if city_name in ALERT_TARGET_CITIES:
        return city_name
    return None

def fetch_alerts():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(ALERT_API_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            return []
        alerts = data.get("data", [])
        result = []
        for alert in alerts:
            title = alert.get("title", "") or alert.get("headline", "")
            if not title:
                continue
            if any(ignore in title for ignore in IGNORE_ALERT_TYPES):
                print(f"忽略预警：{title}")
                continue
            level_match = re.search(r'(蓝色|黄色|橙色|红色)预警', title)
            if not level_match:
                continue
            level = level_match.group(1)
            type_match = re.search(r'([\u4e00-\u9fa5]+)(?:蓝色|黄色|橙色|红色)预警', title)
            alert_type = type_match.group(1) if type_match else "未知"
            city_name = extract_city_from_title(title)
            if not city_name:
                print(f"无法从标题提取城市：{title}")
                continue
            target = city_to_target(city_name)
            if not target:
                print(f"城市 {city_name} 不在目标列表中，标题：{title}")
                continue
            effective = alert.get("effective", "")
            pub_time = effective
            if pub_time:
                try:
                    dt = datetime.strptime(pub_time, "%Y/%m/%d %H:%M")
                    pub_time = dt.strftime("%Y年%m月%d日 %H:%M")
                except:
                    pass
            result.append({
                "type": alert_type,
                "level": level,
                "city": target,
                "pub_time": pub_time
            })
        return result
    except Exception as e:
        print(f"获取预警失败：{e}")
        return []

def group_alerts_by_type_level(alerts):
    groups = {}
    for alert in alerts:
        key = (alert["type"], alert["level"])
        if key not in groups:
            groups[key] = {"type": alert["type"], "level": alert["level"], "cities": set(), "pub_time": alert["pub_time"]}
        groups[key]["cities"].add(alert["city"])
    return [{"type": g["type"], "level": g["level"], "cities": sorted(g["cities"]), "pub_time": g["pub_time"]} for g in groups.values()]

def get_alert_signature(alert):
    return f"{alert['type']}_{','.join(alert['cities'])}"

def load_alert_cache():
    if not os.path.exists(ALERT_CACHE_FILE):
        return {"date": "", "signatures": []}
    try:
        with open(ALERT_CACHE_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != get_current_beijing_date():
            return {"date": "", "signatures": []}
        return data
    except:
        return {"date": "", "signatures": []}

def save_alert_cache(signatures):
    with open(ALERT_CACHE_FILE, "w") as f:
        json.dump({"date": get_current_beijing_date(), "signatures": signatures}, f)

def get_prevention_tips(alert_type, level):
    base = "📌 山西东风南方温馨提示："
    if "暴雨" in alert_type:
        return base + ("立即将露天展车转移至室内，检查排水系统，暂停户外试驾。" if level in ["橙色","红色"] else "提前转移低洼处车辆，清理排水口，注意观察雨势。")
    if "大风" in alert_type or "雷暴大风" in alert_type:
        return base + ("立即加固广告牌，停止户外作业，车辆远离大树和建筑。" if level in ["橙色","红色"] else "检查户外设施，提醒注意高空坠物。")
    if "冰雹" in alert_type:
        return base + "立即将露天车辆转移至室内或覆盖防雹车衣；人员进入室内躲避。"
    if "雪" in alert_type:
        return base + ("检查屋顶承重，及时清理积雪，注意行车安全。" if "暴雪" in alert_type or "大雪" in alert_type else "注意路面湿滑，减少户外活动。")
    return base + "关注天气变化，做好防范。"

def build_alert_message(alert):
    msg = f"""【山西气象预警】
⚠️ {alert['type']}{alert['level']}预警
影响城市：{'、'.join(alert['cities'])}
发布时间：{alert['pub_time']}

{get_prevention_tips(alert['type'], alert['level'])}

请各单位立即响应，做好防范。"""
    return msg

def run_alert_check():
    print("开始检查气象预警...")
    alerts = fetch_alerts()
    if not alerts:
        print("未获取到任何预警")
        return
    grouped = group_alerts_by_type_level(alerts)
    print(f"合并后得到 {len(grouped)} 个预警组")
    cache = load_alert_cache()
    sent = set(cache["signatures"])
    new_alerts = []
    for alert in grouped:
        sig = get_alert_signature(alert)
        if sig not in sent:
            new_alerts.append(alert)
            sent.add(sig)
        else:
            print(f"跳过已发送：{alert['type']}{alert['level']} {alert['cities']}")
    if not new_alerts:
        print("没有需要推送的新预警")
        return
    for alert in new_alerts:
        send_to_wecom(build_alert_message(alert))
    save_alert_cache(list(sent))
    print(f"已推送 {len(new_alerts)} 条预警")

# ======================== 主入口 ========================
if __name__ == "__main__":
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    print(f"当前北京时间: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
    if not is_beijing_time_between(8, 21):
        print("当前不在8:00-21:00之间，脚本退出")
        exit(0)
    if now_bj.hour == 8:
        print("===== 执行每日天气预报推送 =====")
        run_daily_forecast()
        print("===== 执行预警检查 =====")
        run_alert_check()
    else:
        print("===== 执行预警检查 =====")
        run_alert_check()
