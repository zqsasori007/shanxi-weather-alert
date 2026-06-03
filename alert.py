import requests
import xml.etree.ElementTree as ET
import re

# 中国气象局山西省官方预警RSS源（已更新为最新HTTPS地址，永久免费）
RSS_URL = "https://www.nmc.cn/rss/warning/140000.xml"
# 企业微信群机器人Webhook地址（已经是你的地址，不用改）
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2eaff206-0af2-4a1f-b64b-7b88270d5b1b"

def clean_text(text):
    """清理文本中的特殊字符，防止JSON格式错误"""
    if not text:
        return ""
    # 移除换行符、制表符、回车符
    text = re.sub(r'[\n\r\t]', '', text)
    # 移除多余的空格
    text = re.sub(r'\s+', ' ', text)
    # 移除不可见字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text.strip()

def get_prevention_tips(title):
    """根据预警标题自动匹配对应的4S店专属防范提示，未匹配则返回None"""
    title = title.lower()
    
    # 暴雨预警（山西夏季最常见，危害最大）
    if "暴雨" in title:
        return """⚠️ 【山西气象灾害-暴雨天气预警】
1. 立即将所有露天车辆移至室内或地势较高处，无法转移的用加厚防雨布全覆盖
2. 暂停户外试驾活动
3. 检查展厅、库房、停车场排水系统，清理排水沟和雨水井
4. 准备沙袋、挡水板，封堵配电房、监控室等关键区域入口
5. 关闭所有户外用电设备电源，加固充电桩防雨
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    # 大风预警（山西春季多发，易吹倒广告牌砸车）
    elif "大风" in title or "雷暴大风" in title:
        return """⚠️ 【山西气象灾害-大风天气预警】
1. 立即加固所有户外广告牌、易拉宝、遮阳棚、指示牌
2. 将露天车辆移至建筑物背风面，远离大树和高空坠物区域
3. 暂停所有户外试驾活动，关闭展厅玻璃门
4. 检查屋顶是否有松动物品，及时清理高空杂物
5. 提醒员工不要在户外逗留，注意高空坠物安全
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    # 冰雹预警（山西夏季多发，对车辆损害极大）
    elif "冰雹" in title:
        return """⚠️ 【山西气象灾害-冰雹天气预警】
1. 立即将所有露天车辆转移至室内或车库
2. 无法转移的车辆用专用防冰雹车衣或厚棉被覆盖
3. 关闭所有门窗和玻璃幕墙，检查天窗是否关闭严密
4. 暂停所有户外作业，所有人员立即进入室内躲避
5. 冰雹过后不要立即移动车辆，先检查车身和玻璃是否受损
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    # 暴雪预警（山西冬季多发）
    elif "暴雪" in title:
        return """⚠️ 【山西气象灾害-暴雪天气预警】
1. 检查展厅、库房屋顶承重，及时清理积雪防止坍塌
2. 准备除雪工具和融雪剂，提前清理门口和通道积雪
3. 暂停所有户外试驾活动，注意道路交通安全
4. 检查车辆防冻液和电瓶，确保救援车辆随时可用
5. 提醒员工、客户、合作二级网点注意安全防护"""
    
    # 高温预警（山西夏季多发）
    elif "高温" in title:
        return """⚠️ 【山西气象灾害-高温天气预警】
1. 检查露天展车电瓶和轮胎，避免长时间暴晒
2. 展厅空调提前开启，确保客户和员工舒适
3. 准备防暑降温物资（藿香正气水、矿泉水等）
4. 避免在正午高温时段进行户外作业和试驾
5. 检查消防设施，防止车辆自燃和火灾事故
6. 提醒员工、客户、合作二级网点注意安全防护"""
    
    # 雷电预警
    elif "雷电" in title:
        return """⚠️ 【山西气象灾害-雷电天气预警】
1. 暂停所有户外试驾和作业，所有人员立即进入室内
2. 关闭不必要的电器设备，拔掉电源插头
3. 不要靠近窗户、金属管道和避雷针
4. 不要在露天、空旷场所使用手机和固定电话通话
5. 检查防雷设施是否正常工作"""

    # 未匹配到以上6种类型，返回None表示不推送
    return None

def get_latest_alert():
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
        print(f"获取预警失败: {e}")
        return None

def send_to_wechat(alert):
    prevention_tips = get_prevention_tips(alert["title"])
    
    # 核心修改：如果没有匹配到指定的6种预警，直接返回，不发送任何消息
    if not prevention_tips:
        print(f"过滤非指定预警类型: {alert['title']}")
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
    try:
        response = requests.post(WEBHOOK_URL, json=message, timeout=10)
        response.raise_for_status()
        print("预警推送成功")
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == "__main__":
    latest_alert = get_latest_alert()
    if latest_alert:
        send_to_wechat(latest_alert)
    else:
        print("当前无预警信息")
