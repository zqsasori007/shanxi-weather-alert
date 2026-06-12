name: 山西东风南方天气预警

on:
  schedule:
    # 每小时的第5分钟运行一次（UTC时间），对应北京时间每小时的第5分钟
    - cron: '5 * * * *'
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false

jobs:
  weather-bot:
    runs-on: ubuntu-latest
    steps:
      - name: 检出代码
        uses: actions/checkout@v4

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      # 新增：恢复缓存文件
      - name: 恢复缓存
        uses: actions/cache@v4
        with:
          path: |
            forecast_sent_date.txt
            alert_cache.json
          key: weather-cache-${{ github.run_id }}
          restore-keys: |
            weather-cache-

      - name: 安装依赖
        run: pip install requests lxml

      - name: 运行天气脚本
        run: python alert.py

      # 新增：保存缓存文件（即使脚本失败也保存，以便下次运行）
      - name: 保存缓存
        uses: actions/cache@v4
        with:
          path: |
            forecast_sent_date.txt
            alert_cache.json
          key: weather-cache-${{ github.run_id }}
