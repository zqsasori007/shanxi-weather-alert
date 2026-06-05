import requests
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime

# =========配置区（无需修改）=========
# 中国气象局山西省官方预警RSS源（永久免费）
RSS_URL = "https://www.nmc.cn/rss/warning/140000.xml"
# 企业微信群机器人Webhook地址列表
WEBHOOK_URLS = [
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"
]
# 防重复推送缓存文件
CACHE_FILE = "weather_cache.txt"
# 太原未来3天预报地址
FORECAST_URL = "http://www.nmc.cn/publish/forecast/ASX/taiyuan.html"
# 全灾害触发关键词（满足任意一个即推送预报提醒）
WARN_KEYWORDS = ["中雨","大雨","暴雨","大暴雨","大风","雷暴大风","冰雹","暴雪","大雪","高温","雷电","雷阵雨"]
# ===================================

def clean_text(text):
    """清理文本中的特殊字符，防止JSON格式错误"""
    if not text:
        return ""
    text = re.sub(r'[\n\r\t]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text.strip()

def get_prevention_tips(title):
    """根据官方预警标题匹配4S店专属防范提示"""
    title = title.lower()
    
    if "暴雨" in title:
        return """⚠️ 【山西气象灾害-暴雨天气预警】
1. 立即将所有露天车辆移至室内或地势较高处，无法转移的用加厚防雨布全覆盖
2. 暂停户外试驾活动
3. 检查展厅、库房、停车场排水系统，清理排水沟和雨水井
4. 准备沙袋、挡水板，封堵配电房、监控室等关键区域入口
5. 关闭所有户外用电设备电源，加固充电桩防雨
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "大风" in title or "雷暴大风" in title:
        return """⚠️ 【山西气象灾害-大风天气预警】
1. 立即加固所有户外广告牌、易拉宝、遮阳棚、指示牌
2. 将露天车辆移至建筑物背风面，远离大树和高空坠物区域
3. 暂停所有户外试驾活动，关闭展厅玻璃门
4. 检查屋顶是否有松动物品，及时清理高空杂物
5. 提醒员工不要在户外逗留，注意高空坠物安全
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "冰雹" in title:
        return """⚠️ 【山西气象灾害-冰雹天气预警】
1. 立即将所有露天车辆转移至室内或车库
2. 无法转移的车辆用专用防冰雹车衣或厚棉被覆盖
3. 关闭所有门窗和玻璃幕墙，检查天窗是否关闭严密
4. 暂停所有户外作业，所有人员立即进入室内躲避
5. 冰雹过后不要立即移动车辆，先检查车身和玻璃是否受损
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "暴雪" in title:
        return """⚠️ 【山西气象灾害-暴雪天气预警】
1. 检查展厅、库房屋顶承重，及时清理积雪防止坍塌
2. 准备除雪工具和融雪剂，提前清理门口和通道积雪
3. 暂停所有户外试驾活动，注意道路交通安全
4. 检查车辆防冻液和电瓶，确保救援车辆随时可用
5. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "高温" in title:
        return """⚠️ 【山西气象灾害-高温天气预警】
1. 检查露天展车电瓶和轮胎，避免长时间暴晒
2. 展厅空调提前开启，确保客户和员工舒适
3. 准备防暑降温物资（藿香正气水、矿泉水等）
4. 避免在正午高温时段进行户外作业和试驾
5. 检查消防设施，防止车辆自燃和火灾事故
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    elif "雷电" in title:
        return """⚠️ 【山西气象灾害-雷电天气预警】
1. 暂停所有户外试驾和作业，所有人员立即进入室内
2. 关闭不必要的电器设备，拔掉电源插头
3. 不要靠近窗户、金属管道和避雷针
4. 不要在露天、空旷场所使用手机和固定电话通话
5. 检查防雷设施是否正常工作"""

    return None

def get_latest_alert():
    """获取山西省最新官方气象预警"""
    try:
        response = requests.get(RSS_URL, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        channel = root.find('channel')
        items = channel.findall('item')
        if items:
            latest = items[0]
            return {
                "title": clean_text(latest.find('title').text),
                "description": clean_text(latest.find('description').text),
                "pubDate": clean_text(latest.find('pubDate').text)
            }
        return None
    except Exception as e:
        print(f"获取官方预警失败: {e}")
        return None

def send_official_alert(alert):
    """推送官方气象预警到企业微信"""
    prevention_tips = get_prevention_tips(alert["title"])
    
    if not prevention_tips:
        print(f"过滤非指定官方预警类型: {alert['title']}")
        return

    content = f"""【山西省气象预警紧急提醒】
{alert['title']}
发布时间：{alert['pubDate']}
预警详情：{alert['description']}

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
            print(f"官方预警推送成功到: {webhook_url}")
        except Exception as e:
            print(f"官方预警推送失败到 {webhook_url}: {e}")

def get_last_send_date():
    """读取上次推送日期，防止同一天重复群发"""
    if not os.path.exists(CACHE_FILE):
        return ""
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def save_last_send_date():
    """写入今日日期，标记已推送"""
    today = datetime.now().strftime("%Y-%m-%d")
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(today)

def get_3day_forecast():
    """精准抓取太原未来3天（今天+明天+后天）的天气预报"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(FORECAST_URL, headers=headers, timeout=15)
        response.encoding = "utf-8"
        tree = ET.HTML(response.text)
        
        # 提取未来3天的天气描述（中央气象台页面固定结构）
        day_divs = tree.xpath('//*[@id="day7"]/div[position()<=3]')
        all_weather_text = ""
        for div in day_divs:
            all_weather_text += " " + "".join(div.itertext())
        
        # 匹配灾害关键词
        hit_keywords = [k for k in WARN_KEYWORDS if k in all_weather_text]
        return list(set(hit_keywords))  # 去重
    except Exception as e:
        print(f"获取未来3天预报失败: {e}")
        return []

def send_forecast_alert(hit_keywords):
    """推送未来3天灾害天气预报提醒"""
    weather_text = "、".join(hit_keywords)
    content = f"""【太原未来3天灾害天气提前预警】
⚠️ 预报出现：{weather_text}
门店提前防范提示：
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
    # 第一部分：原有官方气象预警推送（不变）
    latest_alert = get_latest_alert()
    if latest_alert:
        send_official_alert(latest_alert)

    # 第二部分：新增未来3天灾害天气预报推送
    today = datetime.now().strftime("%Y-%m-%d")
    last_send = get_last_send_date()
    hit_keywords = get_3day_forecast()

    # 当天未推送过 + 匹配到灾害天气 → 推送
    if hit_keywords and last_send != today:
        send_forecast_alert(hit_keywords)
        save_last_send_date()
        print(f"已推送今日未来3天天气预警: {hit_keywords}")
    else:
        print("无需要推送的未来3天灾害天气或今日已推送")
