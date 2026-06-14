#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山西东风南方汽车销售服务有限公司 - 天气预警机器人
正式版
- 每天 8:00-9:00 推送全省当天天气预报
- 每小时 8:00-21:00 检查气象预警（仅推送目标城市，忽略高温/雷电）
- 相同类型+等级预警合并为一条消息
- 企业微信错误码校验、消息长度控制、特殊字符清洗
"""

import requests
import json
import os
import re
import time
import logging
from datetime import datetime, timedelta
from lxml import etree
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from pytz import timezone as ZoneInfo

# ======================== 配置区域 ========================
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

FORECAST_CACHE_FILE = "forecast_sent_date.txt"
ALERT_CACHE_FILE = "alert_cache.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======================== 辅助函数 ========================
def get_beijing_now():
    try:
        tz = ZoneInfo("Asia/Shanghai")
        return datetime.now(tz)
    except:
        return datetime.utcnow() + timedelta(hours=8)

def is_beijing_time_between(start_hour, end_hour):
    now_bj = get_beijing_now()
    return start_hour <= now_bj.hour < end_hour

def get_current_beijing_date():
    return get_beijing_now().strftime("%Y-%m-%d")

def get_weekday():
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return weekdays[get_beijing_now().weekday()]

def clean_text(text):
    if not text:
        return ""
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return cleaned.strip()

def send_to_wecom(content):
    if not WEBHOOK_URL:
        logger.error("未设置 WEBHOOK_URL")
        return False
    content = clean_text(content)
    if len(content.encode('utf-8')) > 2048:
        logger.warning("消息超长，将截断")
        content = content[:2000]
    headers = {"Content-Type": "application/json"}
    payload = {"msgtype": "text", "text": {"content": content}}
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                errcode = result.get("errcode", -1)
                if errcode == 0:
                    logger.info("消息发送成功")
                    return True
                else:
                    errmsg = result.get("errmsg", "未知错误")
                    logger.error(f"企业微信返回错误码 {errcode}: {errmsg}")
                    if errcode in (93017, 93018):
                        return False
            else:
                logger.error(f"HTTP错误: {resp.status_code}")
        except Exception as e:
            logger.error(f"发送异常: {e}")
        if attempt < max_retries:
            time.sleep(2 ** attempt)
    return False

# ======================== 天气预报抓取 ========================
def get_city_today_weather(city_name, url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        tree = etree.HTML(resp.text)
        
        # 定位今日天气区块
        today_div = tree.xpath('//div[@class="day7"]/div[1]')
        if not today_div:
            today_div = tree.xpath('//*[@id="day7"]/div[1]')
        if not today_div:
            today_div = tree.xpath('//div[contains(@class, "day")]/div[1]')
        if not today_div:
            logger.warning(f"{city_name}: 未找到天气区块")
            return None
        
        div = today_div[0]
        
        # 天气现象
        weather_ele = div.xpath('.//p[@class="wea"]/text()')
        if not weather_ele:
            weather_ele = div.xpath('.//p[contains(@class, "wea")]/text()')
        if weather_ele:
            weather = weather_ele[0].strip()
        else:
            text = "".join(div.itertext())
            match = re.search(r'(晴|多云|阴|小雨|中雨|大雨|暴雨|雷阵雨|冰雹|雪|雾)', text)
            weather = match.group(1) if match else ""
        
        # 温度
        temp_ele = div.xpath('.//p[@class="tem"]/span/text()')
        if len(temp_ele) >= 2:
            temp_high = temp_ele[0].strip()
            temp_low = temp_ele[1].strip()
            temp_str = f"{temp_low}~{temp_high}℃"
        elif len(temp_ele) == 1:
            temp_str = f"{temp_ele[0].strip()}℃"
        else:
            full_text = "".join(div.itertext())
            temps = re.findall(r'(\d+)℃', full_text)
            if temps:
                if len(temps) >= 2:
                    temp_str = f"{temps[1]}~{temps[0]}℃"
                else:
                    temp_str = f"{temps[0]}℃"
            else:
                temp_str = "?"
        
        # 风力
        wind_ele = div.xpath('.//p[@class="win"]/text()')
        if not wind_ele:
            wind_ele = div.xpath('.//p[contains(@class, "win")]/text()')
        if wind_ele:
            wind = wind_ele[0].strip()
        else:
            text = "".join(div.itertext())
            match = re.search(r'([北南西东][风转].*?级|微风|无持续风向)', text)
            wind = match.group(1) if match else ""
        
        if weather and temp_str and wind:
            return f"{weather}，气温{temp_str}，{wind}"
        elif weather and temp_str:
            return f"{weather}，气温{temp_str}"
        else:
            # 保底：返回原始文本片段
            raw = "".join(div.itertext()).strip()[:100]
            return raw
    except Exception as e:
        logger.error(f"{city_name} 抓取失败: {e}")
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
        logger.info(f"{city}: {detail}")
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
        last_line = lines[-1].rstrip("；") + "。"
        lines[-1] = last_line
    lines.append("")
    lines.append("⚠️ 温馨提示：请各单位密切关注实时气象预警，如遇极端天气请做好车辆防护、排水检查等应急工作；提醒员工及合作单位做好人员及财产安全防护！")
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
        logger.info("今日天气预报已发送过，跳过")
        return
    logger.info("开始获取全省当天天气预报...")
    weather, any_success = get_all_cities_weather()
    if not any_success:
        logger.warning("所有城市天气获取失败，本次不推送，不标记已发送")
        return
    if not weather:
        logger.warning("未获取到任何城市的天气数据，标记已发送避免重复尝试")
        mark_forecast_sent()
        return
    msg = build_today_forecast_message(weather)
    if msg:
        if send_to_wecom(msg):
            mark_forecast_sent()
        else:
            logger.error("天气预报推送失败，未标记已发送")
    else:
        logger.warning("消息为空，不推送")

# ======================== 气象预警 ========================
def extract_city_from_title(title):
    # 模式1：省XX市
    match = re.search(r'省(.+?)市', title)
    if match:
        city = match.group(1)
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', city):
            return city
    # 模式2：直接匹配“XX市”且前面不是“省”或“中国”
    match = re.search(r'(?<!省)(?<!中国)([\u4e00-\u9fa5]{2,4})市', title)
    if match:
        city = match.group(1)
        if city not in ['山西', '全省']:
            return city
    # 模式3：从“发布”前查找
    match = re.search(r'([\u4e00-\u9fa5]{2,4})市[^省]', title)
    if match:
        city = match.group(1)
        if city not in ['山西', '全省']:
            return city
    return None

def fetch_alerts_with_retry():
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(ALERT_API_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", [])
            else:
                logger.warning(f"预警接口返回错误码: {data.get('code')}")
        except Exception as e:
            logger.error(f"获取预警失败 (尝试 {attempt+1}/{max_retries+1}): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return []

def fetch_alerts():
    alerts = fetch_alerts_with_retry()
    result = []
    for alert in alerts:
        title = alert.get("title", "") or alert.get("headline", "")
        if not title:
            continue
        if any(ignore in title for ignore in IGNORE_ALERT_TYPES):
            logger.info(f"忽略预警：{title}")
            continue
        level_match = re.search(r'(蓝色|黄色|橙色|红色)预警', title)
        if not level_match:
            continue
        level = level_match.group(1)
        type_match = re.search(r'([\u4e00-\u9fa5]+)(?:蓝色|黄色|橙色|红色)预警', title)
        alert_type = type_match.group(1) if type_match else "未知"
        alert_type = alert_type.replace('冰霍', '冰雹')
        city = extract_city_from_title(title)
        if not city:
            logger.debug(f"无法提取城市：{title}")
            continue
        if city not in ALERT_TARGET_CITIES:
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
            "city": city,
            "pub_time": pub_time
        })
    return result

def group_alerts_by_type_level(alerts):
    groups = {}
    for alert in alerts:
        key = (alert["type"], alert["level"])
        if key not in groups:
            groups[key] = {
                "type": alert["type"],
                "level": alert["level"],
                "cities": set(),
                "pub_time": alert["pub_time"]
            }
        groups[key]["cities"].add(alert["city"])
    return [{
        "type": g["type"],
        "level": g["level"],
        "cities": sorted(g["cities"]),
        "pub_time": g["pub_time"]
    } for g in groups.values()]

def get_alert_signature(alert):
    return f"{alert['type']}_{','.join(alert['cities'])}"

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
    with open(ALERT_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": get_current_beijing_date(), "signatures": signatures}, f, ensure_ascii=False, indent=2)

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
    cities_text = "、".join(alert["cities"])
    tip = get_prevention_tips(alert["type"], alert["level"])
    return f"""【山西气象预警】
⚠️ {alert['type']}{alert['level']}预警
影响城市：{cities_text}
发布时间：{alert['pub_time']}

{tip}

请各单位立即响应，做好防范。"""

def run_alert_check():
    logger.info("开始检查气象预警...")
    alerts = fetch_alerts()
    if not alerts:
        logger.info("未获取到任何预警")
        return
    grouped = group_alerts_by_type_level(alerts)
    logger.info(f"合并后得到 {len(grouped)} 个预警组")
    cache = load_alert_cache()
    sent = set(cache["signatures"])
    new_alerts = []
    for alert in grouped:
        sig = get_alert_signature(alert)
        if sig not in sent:
            new_alerts.append(alert)
            sent.add(sig)
        else:
            logger.info(f"跳过已发送：{alert['type']}{alert['level']} {alert['cities']}")
    if not new_alerts:
        logger.info("没有需要推送的新预警")
        return
    for alert in new_alerts:
        msg = build_alert_message(alert)
        if send_to_wecom(msg):
            logger.info(f"已推送预警：{alert['type']}{alert['level']} {alert['cities']}")
        else:
            logger.error(f"预警推送失败：{alert['type']}{alert['level']} {alert['cities']}")
    save_alert_cache(list(sent))

# ======================== 主入口 ========================
if __name__ == "__main__":
    now_bj = get_beijing_now()
    logger.info(f"当前北京时间: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
    if not is_beijing_time_between(8, 21):
        logger.info("当前不在8:00-21:00之间，脚本退出")
        exit(0)
    # 预报仅在 8:00-9:00 之间推送
    if 8 <= now_bj.hour < 9:
        logger.info("===== 执行每日天气预报推送 =====")
        run_daily_forecast()
        logger.info("===== 执行预警检查 =====")
        run_alert_check()
    else:
        logger.info("===== 执行预警检查 =====")
        run_alert_check()
