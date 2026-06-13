#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山西东风南方汽车销售服务有限公司 - 天气预警机器人
功能：
1. 每天8:00推送全省主要城市未来3天天气预报（含气温、天气现象）
2. 每小时（8:00-21:00）查询气象预警并推送（每个预警每天只发一次）
"""

import requests
import json
import os
import re
from datetime import datetime, timedelta
from lxml import etree

# ======================== 配置区域 ========================
# 请替换成您自己的企业微信群机器人 Webhook 地址
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"

# 预警接口（山西省，adcode=14）
ALERT_API_URL = "https://weather.cma.cn/api/map/alarm?adcode=14"

# 山西主要城市（地级市）的 NMC 预报页面
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

# 区县 → 地级市 映射表
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

# 缓存文件
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

# ======================== 功能1：未来三天天气预报 ========================
def get_city_weather(city_name, url):
    """抓取单个城市未来三天的天气现象和气温，返回字符串列表（每天一行）"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        tree = etree.HTML(resp.text)
        day_divs = tree.xpath('//*[@id="day7"]/div[position()<=3]')
        result = []
        for div in day_divs:
            # 提取日期（从标题获取）
            date_ele = div.xpath('.//h3/text()')
            date_str = date_ele[0].strip() if date_ele else ""
            # 提取天气现象
            weather_ele = div.xpath('.//p[@class="wea"]/text()')
            weather = weather_ele[0].strip() if weather_ele else ""
            # 提取温度（最高/最低）
            temp_ele = div.xpath('.//p[@class="tem"]/span/text()')
            if len(temp_ele) >= 2:
                temp_high = temp_ele[0].strip()
                temp_low = temp_ele[1].strip()
                temp_text = f"{temp_high}/{temp_low}℃"
            elif len(temp_ele) == 1:
                temp_text = f"{temp_ele[0].strip()}℃"
            else:
                # 备用提取：从文本中匹配数字
                full_text = "".join(div.itertext())
                temps = re.findall(r'(\d+)℃', full_text)
                if temps:
                    if len(temps) >= 2:
                        temp_text = f"{temps[0]}/{temps[1]}℃"
                    else:
                        temp_text = f"{temps[0]}℃"
                else:
                    temp_text = "?"
            # 组合：日期 天气 温度
            if date_str:
                line = f"{date_str} {weather} {temp_text}"
            else:
                line = f"{weather} {temp_text}"
            result.append(line)
        return result
    except Exception as e:
        print(f"获取 {city_name} 天气失败：{e}")
        return None

def get_province_weather():
    result = {}
    any_success = False
    for city, url in CITY_FORECAST_URLS.items():
        weathers = get_city_weather(city, url)
        if weathers is None:
            continue
        any_success = True
        if weathers:
            result[city] = weathers
        else:
            print(f"{city} 未获取到有效天气")
    return result, any_success

def build_forecast_message(weather_data):
    """生成天气预报文本消息，格式专业"""
    if not weather_data:
        return None
    today = get_current_beijing_date()
    # 计算未来三天的日期范围
    lines = [f"【山西未来三天天气预报】{today} 发布"]
    lines.append("")
    for city, days in weather_data.items():
        # days 是长度为3的列表，例如 ["06/13 小雨 15℃", "06/14 多云 20℃", "06/15 晴 25℃"]
        forecast_str = " | ".join(days)
        lines.append(f"📍 {city}：{forecast_str}")
    lines.append("")
    lines.append("⚠️ 温馨提示：请各单位关注实时气象预警，做好车辆防护、排水检查、防暑降温等工作。")
    lines.append("📢 数据来源：中央气象台")
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
    if has_forecast_sent_today():
        print("今日天气预报已发送过，跳过")
        return
    print("开始获取全省未来三天天气预报...")
    weather, any_success = get_province_weather()
    
    if not any_success:
        print("所有城市天气获取失败，本次不推送，不标记已发送")
        return
    
    if not weather:
        print("未获取到任何城市的天气数据，标记已发送避免重复尝试")
        mark_forecast_sent()
        return
    
    msg = build_forecast_message(weather)
    if msg:
        send_to_wecom(msg)
        mark_forecast_sent()
    else:
        print("消息为空，不推送")

# ======================== 功能2：实时气象预警 ========================
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
            # 格式化发布时间
            if pub_time:
                try:
                    dt = datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    pub_time = dt.strftime("%Y年%m月%d日 %H:%M")
                except:
                    pass
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
    """专业防范提示（针对汽车销售公司）"""
    base = "📌 山西东风南方温馨提示："
    if "暴雨" in alert_type:
        if level in ["橙色", "红色"]:
            return base + "立即将露天展车转移至室内，无法转移的用防雨布遮盖；检查排水系统，清理排水沟；暂停户外试驾。"
        else:
            return base + "提前转移低洼处车辆，清理排水口，注意观察雨势变化；准备沙袋等防汛物资。"
    elif "大风" in alert_type or "雷暴大风" in alert_type:
        if level in ["橙色", "红色"]:
            return base + "立即加固户外广告牌、易拉宝、遮阳棚；停止户外作业；车辆停放远离大树、建筑边缘和临时搭建物。"
        else:
            return base + "检查户外设施稳固情况，提醒员工注意高空坠物；必要时暂停试驾。"
    elif "冰雹" in alert_type:
        return base + "立即将所有露天车辆转移至室内或覆盖防雹车衣；人员进入室内躲避；关闭门窗。"
    elif "雪" in alert_type:
        if "暴雪" in alert_type or "大雪" in alert_type:
            return base + "检查屋顶承重，及时清理积雪；准备除雪工具和融雪剂；提醒员工行车安全。"
        else:
            return base + "注意路面湿滑，减少户外活动；车辆行驶保持安全距离。"
    elif "高温" in alert_type:
        return base + "展厅空调提前开启，准备防暑药品（藿香正气水、风油精）；检查车辆电瓶和轮胎，避免自燃；提醒客户注意防晒。"
    elif "雷电" in alert_type:
        return base + "暂停户外试驾和作业；关闭不必要的电器；人员进入室内，远离金属门窗和裸露线缆。"
    else:
        return base + "关注天气变化，做好相应防范措施，确保人员和财产安全。"

def build_alert_message(alert):
    level_text = alert["level"]
    cities_text = "、".join(alert["cities"])
    tip = get_prevention_tips(alert["type"], alert["level"])
    msg = f"""【山西气象预警】
⚠️ {alert['type']}{level_text}预警
影响城市：{cities_text}
发布时间：{alert['pub_time']}

{tip}

请各子公司、分公司立即响应，做好防范。"""
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
            print(f"跳过已发送预警：{alert['type']}{alert['level']} 影响 {alert['cities']}")
    
    if not new_alerts:
        print("没有需要推送的新预警")
        return
    
    for alert in new_alerts:
        msg = build_alert_message(alert)
        send_to_wecom(msg)
    
    save_alert_cache(list(sent_signatures))
    print(f"已推送 {len(new_alerts)} 条新预警")

# ======================== 主入口 ========================
if __name__ == "__main__":
    now_utc = datetime.utcnow()
    now_bj = now_utc + timedelta(hours=8)
    current_hour = now_bj.hour
    
    print(f"当前北京时间: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not is_beijing_time_between(8, 21):
        print("当前不在8:00-21:00之间，脚本退出")
        exit(0)
    
    if current_hour == 8:
        print("===== 执行每日天气预报推送 =====")
        run_daily_forecast()
        print("===== 执行预警检查 =====")
        run_alert_check()
    else:
        print("===== 执行预警检查 =====")
        run_alert_check()
