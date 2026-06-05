name: Shanxi Weather Alert

on:
  schedule:
    # 北京时间8:00-18:00每小时运行一次（UTC 0:00-10:00）
    - cron: '0 0-10 * * *'
  workflow_dispatch:  # 允许手动触发测试

jobs:
  alert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests
      - name: Run alert script
        run: python alert.py
