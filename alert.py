import requests
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime, timedelta

# =========配置区（无需修改）=========
# 中国气象局山西省官方预警JSON接口（永久免费，2026年最新）
ALERT_API_URL = "https://weather.cma.cn/api/map/alarm?adcode=14"
# 企业微信群机器人Webhook地址列表
WEBHOOK_URLS = [
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"
]
# 防重复推送缓存文件
CACHE_FILE = "weather_cache.txt"
# 预警类型缓存文件（记录当天已发送的预警类型）
ALERT_TYPE_CACHE = "alert_type_cache.txt"
# 山西全省11个地级市未来3天预报地址
CITY_FORECAST_URLS = [
    "http://www.nmc.cn/publish/forecast/ASX/taiyuan.html",  # 太原
    "http://www.nmc.cn/publish/forecast/ASX/datong.html",   # 大同
    "http://www.nmc.cn/publish/forecast/ASX/shuozhou.html", # 朔州
    "http://www.nmc.cn/publish/forecast/ASX/xinzhou.html",  # 忻州
    "http://www.nmc.cn/publish/forecast/ASX/lvliang.html",  # 吕梁
    "http://www.nmc.cn/publish/forecast/ASX/jinzhong.html", # 晋中
    "http://www.nmc.cn/publish/forecast/ASX/yangquan.html", # 阳泉
    "http://www.nmc.cn/publish/forecast/ASX/changzhi.html", # 长治
    "http://www.nmc.cn/publish/forecast/ASX/jincheng.html", # 晋城
    "http://www.nmc.cn/publish/forecast/ASX/linfen.html",   # 临汾
    "http://www.nmc.cn/publish/forecast/ASX/yuncheng.html"  # 运城
]
# 全灾害触发关键词（满足任意一个即推送预报提醒）
WARN_KEYWORDS = ["中雨","大雨","暴雨","大暴雨","大风","雷暴大风","冰雹","暴雪","大雪","高温","雷电","雷阵雨"]
# 山西全省区县-市级映射表（完整）
SHANXI_COUNTY_TO_CITY = {
    # 太原
    "太原": "太原", "小店": "太原", "迎泽": "太原", "杏花岭": "太原", "尖草坪": "太原",
    "万柏林": "太原", "晋源": "太原", "清徐": "太原", "阳曲": "太原", "娄烦": "太原", "古交": "太原",
    # 大同
    "大同": "大同", "平城": "大同", "云冈": "大同", "云州": "大同", "新荣": "大同",
    "阳高": "大同", "天镇": "大同", "广灵": "大同", "灵丘": "大同", "浑源": "大同", "左云": "大同",
    # 朔州
    "朔州": "朔州", "朔城": "朔州", "平鲁": "朔州", "山阴": "朔州", "应县": "朔州", "右玉": "朔州", "怀仁": "朔州",
    # 忻州
    "忻州": "忻州", "忻府": "忻州", "定襄": "忻州", "五台": "忻州", "代县": "忻州", "繁峙": "忻州",
    "宁武": "忻州", "静乐": "忻州", "神池": "忻州", "五寨": "忻州", "岢岚": "忻州", "河曲": "忻州",
    "保德": "忻州", "偏关": "忻州", "原平": "忻州",
    # 吕梁
    "吕梁": "吕梁", "离石": "吕梁", "文水": "吕梁", "交城": "吕梁", "兴县": "吕梁", "临县": "吕梁",
    "柳林": "吕梁", "石楼": "吕梁", "岚县": "吕梁", "方山": "吕梁", "中阳": "吕梁", "交口": "吕梁",
    "孝义": "吕梁", "汾阳": "吕梁",
    # 晋中
    "晋中": "晋中", "榆次": "晋中", "太谷": "晋中", "祁县": "晋中", "平遥": "晋中", "灵石": "晋中",
    "介休": "晋中", "榆社": "晋中", "左权": "晋中", "和顺": "晋中", "昔阳": "晋中", "寿阳": "晋中",
    # 阳泉
    "阳泉": "阳泉", "城区": "阳泉", "矿区": "阳泉", "郊区": "阳泉", "平定": "阳泉", "盂县": "阳泉",
    # 长治
    "长治": "长治", "潞州": "长治", "上党": "长治", "屯留": "长治", "潞城": "长治",
    "襄垣": "长治", "平顺": "长治", "黎城": "长治", "壶关": "长治", "长子": "长治", "武乡": "长治", "沁县": "长治", "沁源": "长治",
    # 晋城
    "晋城": "晋城", "城区": "晋城", "沁水": "晋城", "阳城": "晋城", "陵川": "晋城", "泽州": "晋城", "高平": "晋城",
    # 临汾
    "临汾": "临汾", "尧都": "临汾", "曲沃": "临汾", "翼城": "临汾", "襄汾": "临汾", "洪洞": "临汾",
    "古县": "临汾", "安泽": "临汾", "浮山": "临汾", "吉县": "临汾", "乡宁": "临汾", "大宁": "临汾",
    "隰县": "临汾", "永和": "临汾", "蒲县": "临汾", "汾西": "临汾", "侯马": "临汾", "霍州": "临汾",
    # 运城
    "运城": "运城", "盐湖": "运城", "临猗": "运城", "万荣": "运城", "闻喜": "运城", "稷山": "运城",
    "新绛": "运城", "绛县": "运城", "垣曲": "运城", "夏县": "运城", "平陆": "运城", "芮城": "运城",
    "永济": "运城", "河津": "运城"
}
# ===================================

def clean_text(text):
    """清理文本中的特殊字符，防止JSON格式错误"""
    if not text:
        return ""
    text = re.sub(r'[\n\r\t]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text.strip()

def extract_alert_type_and_level(title):
    """从预警标题中提取预警类型和等级"""
    # 匹配"XX橙色预警"、"XX红色预警"格式
    match = re.search(r'([\u4e00-\u9fa5]+)(橙色|红色)预警', title)
    if match:
        return match.group(1), match.group(2)
    return None, None

def extract_city_name(title):
    """从预警标题中提取市级名称（适配新API所有格式）"""
    # 遍历所有区县名称，找到匹配的
    for county, city in SHANXI_COUNTY_TO_CITY.items():
        if county in title:
            return city
    
    # 如果都没匹配到，返回"山西"
    return "山西"

def get_prevention_tips(alert_type):
    """根据预警类型匹配4S店专属防范提示"""
    alert_type = alert_type.lower()
    
    if "暴雨" in alert_type:
        return """⚠️ 【山西气象灾害-暴雨天气预警】
1. 立即将所有露天车辆移至室内或地势较高处，无法转移的用加厚防雨布全覆盖
2. 暂停户外试驾活动
3. 检查展厅、库房、停车场排水系统，清理排水沟和雨水井
4. 准备沙袋、挡水板，封堵配电房、监控室等关键区域入口
5. 关闭所有户外用电设备电源，加固充电桩防雨
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "大风" in alert_type or "雷暴大风" in alert_type:
        return """⚠️ 【山西气象灾害-大风天气预警】
1. 立即加固所有户外广告牌、易拉宝、遮阳棚、指示牌
2. 将露天车辆移至建筑物背风面，远离大树和高空坠物区域
3. 暂停所有户外试驾活动，关闭展厅玻璃门
4. 检查屋顶是否有松动物品，及时清理高空杂物
5. 提醒员工不要在户外逗留，注意高空坠物安全
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "冰雹" in alert_type:
        return """⚠️ 【山西气象灾害-冰雹天气预警】
1. 立即将所有露天车辆转移至室内或车库
2. 无法转移的车辆用专用防冰雹车衣或厚棉被覆盖
3. 关闭所有门窗和玻璃幕墙，检查天窗是否关闭严密
4. 暂停所有户外作业，所有人员立即进入室内躲避
5. 冰雹过后不要立即移动车辆，先检查车身和玻璃是否受损
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "暴雪" in alert_type or "大雪" in alert_type:
        return """⚠️ 【山西气象灾害-暴雪天气预警】
1. 检查展厅、库房屋顶承重，及时清理积雪防止坍塌
2. 准备除雪工具和融雪剂，提前清理门口和通道积雪
3. 暂停所有户外试驾活动，注意道路交通安全
4. 检查车辆防冻液和电瓶，确保救援车辆随时可用
5. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "高温" in alert_type:
        return """⚠️ 【山西气象灾害-高温天气预警】
1. 检查露天展车电瓶和轮胎，避免长时间暴晒
2. 展厅空调提前开启，确保客户和员工舒适
3. 准备防暑降温物资（藿香正气水、矿泉水等）
4. 避免在正午高温时段进行户外作业和试驾
5. 检查消防设施，防止车辆自燃和火灾事故
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "雷电" in alert_type:
        return """⚠️ 【山西气象灾害-雷电天气预警】
1. 暂停所有户外试驾和作业，所有人员立即进入室内
2. 关闭不必要的电器设备，拔掉电源插头
3. 不要靠近窗户、金属管道和避雷针
4. 不要在露天、空旷场所使用手机和固定电话通话
5. 检查防雷设施是否正常工作"""

    return None

def get_last_send_date():
    """读取上次推送日期，防止同一天重复群发预报"""
    if not os.path.exists(CACHE_FILE):
        return ""
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_last_send_date():
    """写入今日日期，标记预报已推送（使用北京时间）"""
    now_utc = datetime.utcnow()
    now = now_utc + timedelta(hours=8)
    today = now.strftime("%Y-%m-%d")
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(today)

def get_alert_type_cache():
    """读取当天已发送的预警类型列表（使用北京时间）"""
    now_utc = datetime.utcnow()
    now = now_utc + timedelta(hours=8)
    today = now.strftime("%Y-%m-%d")
    
    # 如果缓存文件不存在，返回空列表
    if not os.path.exists(ALERT_TYPE_CACHE):
        return []
    
    # 读取缓存文件内容
    with open(ALERT_TYPE_CACHE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    
    # 如果缓存文件为空，返回空列表
    if not lines:
        return []
    
    # 第一行是缓存日期
    cache_date = lines[0]
    
    # 如果缓存日期不是今天，清空缓存并返回空列表
    if cache_date != today:
        with open(ALERT_TYPE_CACHE, "w", encoding="utf-8") as f:
            f.write(today + "\n")
        return []
    
    # 返回今天已发送的预警类型列表
    return lines[1:]

def save_alert_type_cache(alert_type):
    """保存预警类型到当天缓存（使用北京时间）"""
    now_utc = datetime.utcnow()
    now = now_utc + timedelta(hours=8)
    today = now.strftime("%Y-%m-%d")
    existing_types = get_alert_type_cache()
    
    # 如果该类型已经存在，不重复保存
    if alert_type in existing_types:
        return
    
    # 写入缓存文件
    with open(ALERT_TYPE_CACHE, "w", encoding="utf-8") as f:
        f.write(today + "\n")
        for t in existing_types:
            f.write(t + "\n")
        f.write(alert_type + "\n")

def get_all_high_level_alerts():
    """获取山西省所有当前有效的橙色和红色预警"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(ALERT_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        alerts_by_type = {}
        sent_types = get_alert_type_cache()
        
        if data["code"] != 0 or not data["data"]:
            return {}
        
        for alert in data["data"]:
            title = clean_text(alert["headline"])
            description = clean_text(alert["description"])
            pubDate = clean_text(alert["effective"])
            
            # 提取预警类型和等级
            alert_type, alert_level = extract_alert_type_and_level(title)
            
            # 只保留橙色和红色预警
            if not alert_level or alert_level not in ["橙色", "红色"]:
                continue
            
            # 如果该类型今天已经发送过，跳过
            if alert_type in sent_types:
                continue
            
            # 按预警类型分组
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = {
                    "level": alert_level,
                    "cities": [],
                    "description": description,
                    "pubDate": pubDate
                }
            
            # 提取市级名称并添加到列表（自动去重）
            city_name = extract_city_name(title)
            if city_name not in alerts_by_type[alert_type]["cities"]:
                alerts_by_type[alert_type]["cities"].append(city_name)
        
        return alerts_by_type
    except Exception as e:
        print(f"获取官方预警失败: {e}")
        return {}

def send_alert(alert_type, alert_data):
    """发送预警消息"""
    cities_text = "、".join(alert_data["cities"])
    prevention_tips = get_prevention_tips(alert_type)
    
    if not prevention_tips:
        print(f"过滤非指定预警类型: {alert_type}")
        return

    # 红色预警单独标记
    level_text = "红色" if alert_data["level"] == "红色" else "橙色"
    
    content = f"""【山西省气象预警紧急提醒】
今日{level_text}{alert_type}预警汇总
发布时间：{alert_data['pubDate']}
预警城市：{cities_text}
预警详情：上述城市受天气系统影响，请注意防范。

{prevention_tips}"""

    message = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    for webhook_url in WEBHOOK_URLS:
        try:
            response = requests.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
            print(f"{level_text}{alert_type}预警推送成功")
        except Exception as e:
            print(f"{level_text}{alert_type}预警推送失败: {e}")
    
    # 标记该预警类型今天已发送
    save_alert_type_cache(alert_type)

def get_province_3day_forecast():
    """抓取山西全省11个地级市未来3天的天气预报"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    all_hit_keywords = set()  # 使用集合自动去重
    
    for city_url in CITY_FORECAST_URLS:
        try:
            response = requests.get(city_url, headers=headers, timeout=8)
            response.encoding = "utf-8"
            tree = ET.HTML(response.text)
            
            # 提取未来3天的天气描述
            day_divs = tree.xpath('//*[@id="day7"]/div[position()<=3]')
            city_weather_text = ""
            for div in day_divs:
                city_weather_text += " " + "".join(div.itertext())
            
            # 匹配灾害关键词
            for keyword in WARN_KEYWORDS:
                if keyword in city_weather_text:
                    all_hit_keywords.add(keyword)
                    
        except Exception as e:
            print(f"获取城市预报失败: {city_url}, 错误: {e}")
            continue  # 单个城市失败不影响其他城市
    
    return list(all_hit_keywords)

def send_forecast_alert(hit_keywords):
    """推送全省未来3天灾害天气预报提醒"""
    weather_text = "、".join(hit_keywords)
    content = f"""【山西全省未来3天灾害天气提前预警】
⚠️ 预报出现：{weather_text}
全省各门店提前防范提示：
1. 降雨/暴雪：露天展车优先入库，无法入库做好防雨防雪遮盖，排查展厅库房排水
2. 大风/雷电：加固户外广告牌、展架物料，暂停户外试驾作业
3. 高温：注意车辆停放防晒，车间防暑降温，检查电瓶和消防设施
4. 冰雹：提前预留室内车位，预警发布后立即转移所有露天车辆"""

    message = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    for webhook_url in WEBHOOK_URLS:
        try:
            response = requests.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
            print(f"预报提醒推送成功到: {webhook_url}")
        except Exception as e:
            print(f"预报提醒推送失败到 {webhook_url}: {e}")

if __name__ == "__main__":
    # 获取UTC时间并加8小时得到北京时间
    now_utc = datetime.utcnow()
    now = now_utc + timedelta(hours=8)
    
    # 只在北京时间8:00-20:00之间运行所有功能
    if 8 <= now.hour <= 20:
        # 第一部分：全省未来3天预报提醒（固定每天8:00-8:59推送一次）
        if now.hour == 8:
            last_send = get_last_send_date()
            hit_keywords = get_province_3day_forecast()
            
            if hit_keywords and last_send != now.strftime("%Y-%m-%d"):
                send_forecast_alert(hit_keywords)
                save_last_send_date()
                print(f"已推送今日全省未来3天天气预警: {hit_keywords}")
            else:
                print("无需要推送的全省未来3天灾害天气或今日已推送")
        
        # 第二部分：橙色和红色预警推送（每小时检查一次，同类型同一天只发1次）
        all_alerts = get_all_high_level_alerts()
        print(f"获取到{len(all_alerts)}种新的橙色/红色预警")
        for alert_type, alert_data in all_alerts.items():
            print(f"准备推送: {alert_data['level']}{alert_type}预警, 城市: {alert_data['cities']}")
            send_alert(alert_type, alert_data)
    else:
        print(f"非工作时间，系统休眠中。当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
