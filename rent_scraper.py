# -*- coding: utf-8 -*-
import gspread
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import urllib.parse
from datetime import datetime
import pytz
import os

# ===============================================================
# ★★★★★【設定箇所】ここから下をあなたの情報に書き換えてください ★★★★★
# ===============================================================

# 1. Googleスプレッドシートの名前
SPREADSHEET_NAME = "賃料データベース" 

# 2. サービスアカウントのJSONキーファイル名（このままでOK）
SERVICE_ACCOUNT_FILE = 'key.json' 

# 3. データを取得したい市区町村のリスト
TARGET_AREAS = [
    # --- 名古屋・尾張エリア ---
    {"prefecture": "愛知県", "city": "名古屋市千種区"},
    {"prefecture": "愛知県", "city": "名古屋市東区"},
    {"prefecture": "愛知県", "city": "名古屋市北区"},
    {"prefecture": "愛知県", "city": "名古屋市西区"},
    {"prefecture": "愛知県", "city": "名古屋市中村区"},
    {"prefecture": "愛知県", "city": "名古屋市中区"},
    {"prefecture": "愛知県", "city": "名古屋市昭和区"},
    {"prefecture": "愛知県", "city": "名古屋市瑞穂区"},
    {"prefecture": "愛知県", "city": "名古屋市熱田区"},
    {"prefecture": "愛知県", "city": "名古屋市中川区"},
    {"prefecture": "愛知県", "city": "名古屋市港区"},
    {"prefecture": "愛知県", "city": "名古屋市南区"},
    {"prefecture": "愛知県", "city": "名古屋市守山区"},
    {"prefecture": "愛知県", "city": "名古屋市緑区"},
    {"prefecture": "愛知県", "city": "名古屋市名東区"},
    {"prefecture": "愛知県", "city": "名古屋市天白区"},
    {"prefecture": "愛知県", "city": "一宮市"},
    {"prefecture": "愛知県", "city": "瀬戸市"},
    {"prefecture": "愛知県", "city": "春日井市"},
    {"prefecture": "愛知県", "city": "犬山市"},
    {"prefecture": "愛知県", "city": "江南市"},
    {"prefecture": "愛知県", "city": "小牧市"},
    {"prefecture": "愛知県", "city": "稲沢市"},
    {"prefecture": "愛知県", "city": "尾張旭市"},
    {"prefecture": "愛知県", "city": "岩倉市"},
    {"prefecture": "愛知県", "city": "豊明市"},
    {"prefecture": "愛知県", "city": "日進市"},
    {"prefecture": "愛知県", "city": "清須市"},
    {"prefecture": "愛知県", "city": "北名古屋市"},
    {"prefecture": "愛知県", "city": "長久手市"},
    {"prefecture": "愛知県", "city": "東郷町"},
    {"prefecture": "愛知県", "city": "豊山町"},
    {"prefecture": "愛知県", "city": "大口町"},
    {"prefecture": "愛知県", "city": "扶桑町"},
    {"prefecture": "愛知県", "city": "津島市"},
    {"prefecture": "愛知県", "city": "愛西市"},
    {"prefecture": "愛知県", "city": "弥富市"},
    {"prefecture": "愛知県", "city": "あま市"},
    {"prefecture": "愛知県", "city": "大治町"},
    {"prefecture": "愛知県", "city": "蟹江町"},
    {"prefecture": "愛知県", "city": "飛島村"},
    {"prefecture": "愛知県", "city": "半田市"},
    {"prefecture": "愛知県", "city": "常滑市"},
    {"prefecture": "愛知県", "city": "東海市"},
    {"prefecture": "愛知県", "city": "大府市"},
    {"prefecture": "愛知県", "city": "知多市"},
    {"prefecture": "愛知県", "city": "阿久比町"},
    {"prefecture": "愛知県", "city": "東浦町"},
    {"prefecture": "愛知県", "city": "南知多町"},
    {"prefecture": "愛知県", "city": "美浜町"},
    {"prefecture": "愛知県", "city": "武豊町"},

    # --- 西三河・東三河エリア ---
    {"prefecture": "愛知県", "city": "岡崎市"},
    {"prefecture": "愛知県", "city": "碧南市"},
    {"prefecture": "愛知県", "city": "刈谷市"},
    {"prefecture": "愛知県", "city": "豊田市"},
    {"prefecture": "愛知県", "city": "安城市"},
    {"prefecture": "愛知県", "city": "西尾市"},
    {"prefecture": "愛知県", "city": "知立市"},
    {"prefecture": "愛知県", "city": "高浜市"},
    {"prefecture": "愛知県", "city": "みよし市"},
    {"prefecture": "愛知県", "city": "幸田町"},
    {"prefecture": "愛知県", "city": "豊橋市"},
    {"prefecture": "愛知県", "city": "豊川市"},
    {"prefecture": "愛知県", "city": "蒲郡市"},
    {"prefecture": "愛知県", "city": "新城市"},
    {"prefecture": "愛知県", "city": "田原市"},
    {"prefecture": "愛知県", "city": "設楽町"},
    {"prefecture": "愛知県", "city": "東栄町"},
    {"prefecture": "愛知県", "city": "豊根村"},
]

# (参考) その他の設定
PROPERTY_TYPES = { "mansion": True, "apaato": True, "kodate": True }
MAX_PAGES_PER_AREA = 1

# ===============================================================
# ★★★★★【設定箇所】はここまでです。これより下は触らないでください ★★★★★
# ===============================================================

# --- ここからプログラム本体 ---

def setup_gspread():
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        spreadsheet = gc.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        print(f"✅ Log: Googleスプレッドシート「{SPREADSHEET_NAME}」への接続に成功しました。")
        return worksheet
    except Exception as e:
        print(f"❌ Error: Googleスプレッドシートに接続できませんでした。ファイル名や共有設定を確認してください。")
        print(f"   詳細: {e}")
        return None

def get_suumo_data(pref_name, city, property_types, pages):
    print(f"  > Processing: {pref_name} {city}")
    pref_map = {'北海道': '01', '青森県': '02', '岩手県': '03', '宮城県': '04', '秋田県': '05', '山形県': '06', '福島県': '07', '茨城県': '08', '栃木県': '09', '群馬県': '10', '埼玉県': '11', '千葉県': '12', '東京都': '13', '神奈川県': '14', '新潟県': '15', '富山県': '16', '石川県': '17', '福井県': '18', '山梨県': '19', '長野県': '20', '岐阜県': '21', '静岡県': '22', '愛知県': '23', '三重県': '24', '滋賀県': '25', '京都府': '26', '大阪府': '27', '兵庫県': '28', '奈良県': '29', '和歌山県': '30', '鳥取県': '31', '島根県': '32', '岡山県': '33', '広島県': '34', '山口県': '35', '徳島県': '36', '香川県': '37', '愛媛県': '38', '高知県': '39', '福岡県': '40', '佐賀県': '41', '長崎県': '42', '熊本県': '43', '大分県': '44', '宮崎県': '45', '鹿児島県': '46', '沖縄県': '47'}
    base_url = "https://suumo.jp/jj/chintai/ichiran/FR301FC001/?"
    shkr_params = []
    if property_types.get('mansion'): shkr_params.append("shkr1=03")
    if property_types.get('apaato'): shkr_params.append("shkr2=03")
    if property_types.get('kodate'): shkr_params.append("shkr3=03")
    encoded_city = urllib.parse.quote(city)
    params = {"ar": "030", "bs": "040", "ta": pref_map.get(pref_name, ""), "sc_nm": encoded_city, "cb": "0.0", "ct": "9999999", "mb": "0", "mt": "9999999", "et": "9999999", "cn": "9999999", "sngz": "", "DAT_FRM": "1"}
    area_property_list = []
    for page in range(1, pages + 1):
        full_url = base_url + urllib.parse.urlencode(params) + f"&page={page}&" + "&".join(shkr_params)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)
