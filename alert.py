#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests, json, os, re, time, logging
from datetime import datetime, timedelta
from lxml import etree
import pytz

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"
ALERT_API_URL = "https://weather.cma.cn/api/map/alarm?adcode=14"
ALL_CITIES = ["太原", "大同", "朔州", "忻州", "吕梁", "晋中", "阳泉", "长治", "晋城", "临汾", "运城"]
ALERT_TARGET_CITIES = ["太原", "晋中", "吕梁", "阳泉", "忻州", "长治", "运城"]
IGNORE_ALERT_TYPES = ["高温", "雷电"]

CITY_URLS = {
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_beijing_now():
    try: return datetime.now(pytz.timezone('Asia/Shanghai'))
    except: return datetime.utcnow() + timedelta(hours=8)

def send_wecom(content):
    if not WEBHOOK_URL: return False
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    if len(content.encode()) > 2048: content = content[:2000]
    for _ in range(2):
        try:
            r = requests.post(WEBHOOK_URL, json={"msgtype": "text", "text": {"content": content}}, timeout=10)
            if r.status_code == 200 and r.json().get("errcode") == 0:
                logger.info("消息发送成功")
                return True
        except: pass
        time.sleep(2)
    logger.error("发送失败")
    return False

def get_weather(city, url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.encoding = "utf-8"
        tree = etree.HTML(r.text)
        div = tree.xpath('//div[@class="day7"]/div[1]') or tree.xpath('//*[@id="day7"]/div[1]')
        if not div: return None
        txt = "".join(div[0].itertext())
        wea = re.search(r'(晴|多云|阴|小雨|中雨|大雨|暴雨|雷阵雨|冰雹|雪|雾)', txt)
        temps = re.findall(r'(\d+)℃', txt)
        if len(temps) >= 2:
            low, high = sorted([int(temps[0]), int(temps[1])])
            temp = f"{low}~{high}℃"
        else: temp = temps[0] + "℃" if temps else "?"
        wind = re.search(r'([北南西东][风转].*?级|微风)', txt)
        wind = wind.group(1) if wind else ""
        return f"{wea.group(1) if wea else ''}，气温{temp}，{wind}".lstrip("，")
    except Exception as e:
        logger.error(f"{city} 抓取失败: {e}")
        return None

def daily_forecast():
    cache_file = "forecast_sent_date.txt"
    today = get_beijing_now().strftime("%Y-%m-%d")
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            if f.read().strip() == today:
                logger.info("今日预报已发送，跳过")
                return
    logger.info("开始获取全省天气...")
    weather = {}
    for city in ALL_CITIES:
        w = get_weather(city, CITY_URLS.get(city))
        if w: weather[city] = w
    if not weather:
        logger.warning("未获取到任何天气数据")
        return
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][get_beijing_now().weekday()]
    msg = f"【山西省天气预报】{today}（{weekday}） 发布\n\n"
    for city in ALL_CITIES:
        if city in weather: msg += f"📍 {city}：{weather[city]}；\n"
    msg += "\n⚠️ 温馨提示：请各单位密切关注实时气象预警，如遇极端天气请做好车辆防护、排水检查等应急工作；提醒员工及合作单位做好人员及财产安全防护！\n📢 数据来源：中央气象台"
    if send_wecom(msg):
        with open(cache_file, "w") as f: f.write(today)

def extract_city(title):
    m = re.search(r'省(.+?)市', title)
    if m and re.match(r'^[\u4e00-\u9fa5]{2,4}$', m.group(1)): return m.group(1)
    m = re.search(r'(?<!省)(?<!中国)([\u4e00-\u9fa5]{2,4})市', title)
    if m and m.group(1) not in ['山西', '全省']: return m.group(1)
    return None

def extract_alert_type(title):
    known_types = ['雷暴大风', '冰雹', '暴雨', '大风', '暴雪', '大雪', '中雨', '大雨', '雷电', '高温']
    for t in known_types:
        if t in title: return t
    m = re.search(r'发布(.+?)(?:蓝色|黄色|橙色|红色)预警', title)
    if m:
        core = m.group(1).strip()
        for t in known_types:
            if t in core: return t
        return core
    return "未知"

def fetch_alerts_with_retry():
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain, */*", "Referer": "https://weather.cma.cn/"}
    for attempt in range(3):
        try:
            resp = requests.get(ALERT_API_URL, headers=headers, timeout=10)
            logger.info(f"预警接口状态码: {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"非200状态码: {resp.status_code}, 内容预览: {resp.text[:200]}")
                if attempt < 2: time.sleep(2)
                continue
            data = resp.json()
            if data.get("code") == 0: return data.get("data", [])
            else:
                logger.warning(f"接口返回错误码: {data.get('code')}")
                return []
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"JSON解析失败 (尝试 {attempt+1}/3): {e}, 内容预览: {resp.text[:200]}")
            if attempt < 2: time.sleep(3)
        except Exception as e:
            logger.error(f"请求异常 (尝试 {attempt+1}/3): {e}")
            if attempt < 2: time.sleep(2)
    return []

def alerts_check():
    logger.info("开始检查气象预警...")
    alerts_data = fetch_alerts_with_retry()
    if not alerts_data:
        logger.error("预警数据获取失败，跳过本次检查")
        return
    alerts = []
    for a in alerts_data:
        title = a.get("title") or a.get("headline")
        if not title: continue
        if any(k in title for k in IGNORE_ALERT_TYPES): continue
        level_match = re.search(r'(蓝|黄|橙|红)色预警', title)
        if not level_match: continue
        level = {"蓝": "蓝色", "黄": "黄色", "橙": "橙色", "红": "红色"}[level_match.group(1)]
        alert_type = extract_alert_type(title)
        city = extract_city(title)
        if not city or city not in ALERT_TARGET_CITIES: continue
        pub = a.get("effective", "")
        try: pub = datetime.strptime(pub, "%Y/%m/%d %H:%M").strftime("%Y年%m月%d日 %H:%M")
        except: pass
        alerts.append({"type": alert_type, "level": level, "city": city, "pub": pub})
    if not alerts:
        logger.info("未获取到任何关注的预警")
        return
    groups = {}
    for a in alerts:
        key = (a["type"], a["level"])
        if key not in groups:
            groups[key] = {"type": a["type"], "level": a["level"], "cities": set(), "pub": a["pub"]}
        groups[key]["cities"].add(a["city"])
    logger.info(f"合并后得到 {len(groups)} 个预警组")
    cache_file = "alert_cache.json"
    today = get_beijing_now().strftime("%Y-%m-%d")
    cache = {"date": "", "sigs": []}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except: pass
    if cache.get("date") != today:
        cache = {"date": today, "sigs": []}
    sent = set(cache["sigs"])
    new_groups = []
    for g in groups.values():
        # 修改：去重签名只使用预警类型，忽略等级和城市
        sig = g["type"]
        if sig not in sent:
            new_groups.append(g)
            sent.add(sig)
        else:
            logger.info(f"跳过已发送类型：{g['type']}（等级：{g['level']}，城市：{list(g['cities'])}）")
    if not new_groups:
        logger.info("本时段没有需要推送的新预警（类型已发送）")
        return
    now = get_beijing_now()
    time_str = now.strftime("%Y-%m-%d %H:%M")
    lines = [f"⚠️ 【山西气象预警汇总】预警更新于 {time_str}", ""]
    level_order = {"红色": 0, "橙色": 1, "黄色": 2, "蓝色": 3}
    new_groups.sort(key=lambda x: (x["type"], level_order.get(x["level"], 4)))
    for g in new_groups:
        cities_text = "、".join(sorted(g["cities"]))
        lines.append(f"      {g['type']}{g['level']}预警：{cities_text}")
    lines.append("")
    lines.append("📌 请各单位密切关注极端天气，做好车辆防护、排水检查等应急工作；提醒员工注意个人安全，提醒合作方注意提前防范！")
    msg = "\n".join(lines)
    if send_wecom(msg):
        logger.info(f"已推送汇总预警（{len(new_groups)} 组）")
        with open(cache_file, "w") as f:
            json.dump({"date": today, "sigs": list(sent)}, f)
    else:
        logger.error("汇总预警推送失败")

if __name__ == "__main__":
    now_bj = get_beijing_now()
    logger.info(f"北京时间: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
    if not (8 <= now_bj.hour < 21):
        logger.info("当前不在8:00-21:00之间，脚本退出")
        exit(0)
    daily_forecast()
    alerts_check()
