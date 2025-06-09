import logging
from logging.handlers import RotatingFileHandler
import requests
import json
import random
import pyotp
import base64
import os
import sys
import re
import matplotlib.pyplot as plt
import japanize_matplotlib
from datetime import datetime
import collections
import io

try:
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    GROUP_ID = config["GROUP_ID"]
    WORLD_ID = config["TARGET_WORLD_ID"]
    DISCORD_WEBHOOKS = config["DISCORD_WEBHOOK_URLS"]
    USERNAME = config["USERNAME"]
    PASSWORD = config["PASSWORD"]
    TOTP_SECRET = config["TOTP_SECRET"]
    MIN_USERS = int(config["MINIMUM_USERS"])
    user_agent = config["USER_AGENT"]
except Exception as e:
    print(f"設定ファイル読み込みエラー: {e}")
    exit(1)

API_BASE = "https://api.vrchat.cloud/api/1"

def parse_log_file(log_path):
    timestamps = []
    user_counts = []
    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[GROUP\] グループのオンラインメンバー数:(\d+)'
    )
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    try:
                        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        count = int(match.group(2))
                        timestamps.append(timestamp)
                        user_counts.append(count)
                    except (ValueError, OverflowError) as e:
                        # Skip lines with invalid timestamps or counts
                        logging.debug(f"スキップされた無効な行: {line.strip()} - エラー: {e}")
                        continue
        return timestamps, user_counts
    except FileNotFoundError:
        logging.error(f"エラー: {log_path} が見つかりません")
        return [], []

def analyze_by_hour(timestamps, counts):
    hour_dict = collections.defaultdict(list)
    for ts, count in zip(timestamps, counts):
        hour_dict[ts.hour].append(count)
    return {hour: sum(vals)/len(vals) for hour, vals in hour_dict.items()}

def generate_user_activity_graph():
    log_file = 'vrchat_monitor.log'
    ts, counts = parse_log_file(log_file)
    if not ts or not counts:
        logging.error("グラフ生成: 有効なデータが見つかりませんでした")
        return None
    plt.figure(figsize=(12, 6))
    plt.plot(ts, counts, marker='o', linestyle='-', color='#2ecc71')
    plt.title('VRChat グループオンラインメンバー数の推移')
    plt.xlabel('日時')
    plt.ylabel('オンラインユーザー数')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    img_data = io.BytesIO()
    plt.savefig(img_data, format='png', dpi=300)
    img_data.seek(0)
    plt.close()
    return img_data

def analyze_by_hour(timestamps, counts):
    hour_dict = collections.defaultdict(list)
    for ts, count in zip(timestamps, counts):
        hour_dict[ts.hour].append(count)
    return hour_dict

def generate_hourly_analysis_graph():
    log_file = 'vrchat_monitor.log'
    ts, counts = parse_log_file(log_file)
    if not ts or not counts:
        logging.error("時間帯グラフ生成: 有効なデータが見つかりませんでした")
        return None
    hourly_data = analyze_by_hour(ts, counts)
    ordered_hours = [(h + 12) % 24 for h in range(24)]
    ordered_means = []
    for h in ordered_hours:
        data = hourly_data.get(h, [])
        if data:
            ordered_means.append(sum(data) / len(data))
        else:
            ordered_means.append(0)
    labels = [f"{h}:00" for h in ordered_hours]
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(24), ordered_means, color='#3498db', alpha=0.7, zorder=1)
    for i, h in enumerate(ordered_hours):
        data = hourly_data.get(h, [])
        if len(data) > 0:
            #点を重なりづらく
            x_jitter = [i + (random.random() * 0.4 - 0.2) for _ in range(len(data))]
            plt.scatter(x_jitter, data, color='#e74c3c', alpha=0.7, s=20, zorder=2)
    plt.title('時間帯ごとのオンラインユーザー数分布（平均値とバラツキ）')
    plt.xlabel('時間（24時間表記）')
    plt.ylabel('オンラインユーザー(アカウント)')
    plt.grid(True, axis='y', alpha=0.3)

    plt.xticks(
        range(24),
        labels,
        rotation=45,
        ha='right',
        rotation_mode='anchor'
    )
    plt.tight_layout()
    img_data = io.BytesIO()
    plt.savefig(img_data, format='png', dpi=300)
    img_data.seek(0)
    plt.close()
    return img_data

def send_instance_notification(message):
    logging.info(f"[INSTANCE_NOTIFICATION] {message}")
    try:
        if 'INSTANCE' in DISCORD_WEBHOOKS:
            emoji = '🔔'
            data = {"content": f"{emoji} **[INSTANCE_NOTIFICATION]** {message}"}
            requests.post(DISCORD_WEBHOOKS['INSTANCE'], json=data, timeout=5)
    except Exception as e:
        print(f"Discord通知送信エラー: {e}", file=sys.stderr)

def send_graph_to_discord(webhook_url, title, description=None):
    try:
        # ユーザーアクティビティグラフを生成
        activity_graph = generate_user_activity_graph()
        hourly_graph = generate_hourly_analysis_graph()
        if not activity_graph or not hourly_graph:
            logging.error("グラフ生成に失敗しました")
            return False
        payload = {
            "username": "VRChat Monitor",
            "embeds": [
                {
                    "title": title,
                    "description": description or "VRChatオンラインユーザー統計",
                    "color": 3066993,  # 緑色
                    "image": {"url": "attachment://user_activity.png"}
                }
            ]
        }
        files = {
            "payload_json": (None, json.dumps(payload), "application/json"),
            "user_activity.png": ("user_activity.png", activity_graph, "image/png")
        }
        response = requests.post(webhook_url, files=files, timeout=10)
        if response.status_code in [200, 204]:
            logging.info("アクティビティグラフの送信に成功しました")
            payload2 = {
                "username": "VRChat Monitor",
                "embeds": [
                    {
                        "title": "時間帯別統計",
                        "description": "時間帯ごとの平均オンラインユーザー数",
                        "color": 3447003,  # 青色
                        "image": {"url": "attachment://hourly_analysis.png"}
                    }
                ]
            }
            files2 = {
                "payload_json": (None, json.dumps(payload2), "application/json"),
                "hourly_analysis.png": ("hourly_analysis.png", hourly_graph, "image/png")
            }
            response2 = requests.post(webhook_url, files=files2, timeout=10)
            if response2.status_code in [200, 204]:
                logging.info("アクティビティグラフの送信に成功しました")
                return True
            else:
                logging.error(f"時間帯グラフの送信に失敗: {response2.status_code}, {response2.text}")
                return False
        else:
            logging.error(f"アクティビティグラフの送信に失敗: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logging.error(f"グラフ送信エラー: {e}")
        return False

class DiscordHandler(logging.Handler):
    def __init__(self, webhook_urls, level=logging.WARNING):
        super().__init__(level)
        self.webhook_urls = webhook_urls
    def emit(self, record):
        try:
            emoji = {
                'DEBUG': '🔍',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }.get(record.levelname, '')
            msg = self.format(record)
            data = {"content": f"{emoji} **[{record.levelname}]** {msg}"}
            if record.levelname in ['WARNING', 'ERROR', 'CRITICAL'] and 'LOG' in self.webhook_urls:
                requests.post(self.webhook_urls['LOG'], json=data, timeout=5)
        except Exception as e:
            print(f"Discord通知送信エラー: {e}", file=sys.stderr)

def setup_logging(
    log_file='vrchat_monitor.log',
    discord_webhook_urls=None,
    discord_level=logging.WARNING,
    file_level=logging.INFO
):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger.handlers.clear()
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=10)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if discord_webhook_urls:
        discord_handler = DiscordHandler(discord_webhook_urls, level=discord_level)
        discord_handler.setFormatter(formatter)
        logger.addHandler(discord_handler)
    return logger
def check_auth(session, user_agent):
    try:
        config_resp = session.get(f"{API_BASE}/config", timeout=10, headers={"User-Agent": user_agent})
        api_key = config_resp.json().get("clientApiKey")
        if not api_key:
            logging.error("[AUTH] APIキー取得失敗")
            return None
        # ユーザー名/パスワードをutf-8でbase64エンコード
        credentials = f"{USERNAME}:{PASSWORD}".encode("utf-8")
        encoded_credentials = base64.b64encode(credentials).decode("ascii")
        headers = {
            "User-Agent": user_agent,
            "Authorization": f"Basic {encoded_credentials}"
        }
        auth_resp = session.get(
            f"{API_BASE}/auth/user",
            params={"apiKey": api_key},
            headers=headers,
            timeout=10
        )
        if auth_resp.status_code == 200:
            token = auth_resp.cookies.get("auth")
            logging.info("[AUTH] 認証成功")
            return token
        else:
            logging.warning(f"[AUTH] 認証失敗: {auth_resp.status_code}")
            return None
    except Exception as e:
        logging.error(f"[AUTH] 認証エラー: {e}")
        return None

def verify_totp(session, user_agent):
    otp = pyotp.TOTP(TOTP_SECRET).now()
    try:
        url = f"{API_BASE}/auth/twofactorauth/totp/verify"
        headers = {"User-Agent": user_agent}
        resp = session.post(url, json={"code": otp}, headers=headers, timeout=10)
        if resp.status_code == 200:
            two_factor_cookie = resp.cookies.get("twoFactorAuth")
            if two_factor_cookie:
                with open('auth_cookies.json', 'w') as f:
                    json.dump({
                        "auth": session.cookies.get("auth"),
                        "twoFactorAuth": two_factor_cookie
                    }, f)
                logging.info("[2FA] TOTP認証成功、twoFactorAuthクッキーを保存しました")
            else:
                logging.warning("[2FA] TOTP認証は成功しましたが、twoFactorAuthクッキーが見つかりませんでした")
            return True
        else:
            logging.warning(f"[2FA] TOTP認証失敗: {resp.status_code}")
            return False
    except Exception as e:
        logging.error(f"[2FA] 認証エラー: {e}")
        return False

def check_online(session, group_id, user_agent):
    url = f"{API_BASE}/groups/{group_id}"
    try:
        resp = session.get(url, timeout=10, headers={"User-Agent": user_agent})
        if resp.status_code == 200:
            count = resp.json().get("onlineMemberCount", 0)
            logging.info(f"[GROUP] グループのオンラインメンバー数:{count}")
            return count
        else:
            logging.warning(f"[GROUP] グループ情報取得失敗: {resp.status_code}")
            return 0
    except Exception as e:
        logging.error(f"[GROUP] グループ取得エラー: {e}")
        return 0

def check_group_instance(session, group_id, world_id, user_agent):
    url = f"{API_BASE}/groups/{group_id}/instances"
    try:
        resp = session.get(url, timeout=10, headers={"User-Agent": user_agent})
        if resp.status_code != 200:
            logging.warning(f"[INSTANCE] インスタンス取得失敗: {resp.status_code}")
            return False
        instances = resp.json()
        logging.info(f"[INSTANCE] 取得したインスタンス数: {len(instances)}")
        for inst in instances:
            world = inst.get("world", {})
            current_world_id = world.get("id")
            if current_world_id == world_id:
                logging.info(f"[INSTANCE] 一致するインスタンスを検出: instanceId={inst.get('instanceId')}")
                return True
        logging.info(f"[INSTANCE] 対象ワールド({world_id})のインスタンスは見つかりませんでした")
        return False
    except Exception as e:
        logging.error(f"[INSTANCE] インスタンス取得エラー: {e}")
        return False

def load_saved_cookies():
    try:
        if os.path.exists('auth_cookies.json'):
            with open('auth_cookies.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"[AUTH] 保存されたクッキーの読み込みエラー: {e}")
    return None
def main():
    logger = setup_logging(
        log_file='vrchat_monitor.log',
        discord_webhook_urls=DISCORD_WEBHOOKS,
        discord_level=logging.WARNING,
        file_level=logging.INFO
    )
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    saved_cookies = load_saved_cookies()
    if saved_cookies and "auth" in saved_cookies and "twoFactorAuth" in saved_cookies:
        session.cookies.set("auth", saved_cookies["auth"])
        session.cookies.set("twoFactorAuth", saved_cookies["twoFactorAuth"])
        logging.info("[AUTH] 保存されたクッキーを使用します")
        try:
            verify_resp = session.get(f"{API_BASE}/auth", timeout=10, headers={"User-Agent": user_agent})
            if verify_resp.status_code == 200:
                logging.info("[AUTH] 保存されたクッキーは有効です")
                online_count = check_online(session, GROUP_ID, user_agent)
                if online_count >= MIN_USERS:
                    has_instance = check_group_instance(session, GROUP_ID, WORLD_ID, user_agent)
                    if not has_instance:
                        msg = (
                            "@here 権限保持者各位へ、対象のインスタンスは存在しませんでした。"
                            f"{online_count}人のオンラインのユーザーがあなたを待っています。"
                        )
                        send_instance_notification(msg)
                    else:
                        logging.info("[INSTANCE] 対象ワールドのインスタンスが存在します。通知は行いません。")
                else:
                    logging.info(f"User数が{MIN_USERS}よりも少なかったため、チェックはスキップされました。")
                # グラフを生成して送信（STATSウェブフックがある場合）
                if 'STATS' in DISCORD_WEBHOOKS:
                    send_graph_to_discord(
                        DISCORD_WEBHOOKS['STATS'],
                        "VRChatオンラインユーザー統計",
                        f"現在のオンラインユーザー数: {online_count}人"
                    )
                return
            else:
                logging.warning("[AUTH] 保存されたクッキーは無効です。再認証を行います")
        except Exception as e:
            logging.error(f"[AUTH] クッキー検証エラー: {e}")
    # 通常の認証フロー
    auth_token = check_auth(session, user_agent)
    if not auth_token:
        return
    session.headers.update({"Cookie": f"auth={auth_token}"})
    if verify_totp(session, user_agent):
        online_count = check_online(session, GROUP_ID, user_agent)
        has_instance = check_group_instance(session, GROUP_ID, WORLD_ID, user_agent)
        if not has_instance:
            if online_count >= MIN_USERS:
                msg = (
                    "@権限者 対象のインスタンスは存在しませんでした。"
                    f"{online_count}人のユーザーがあなたを待っています。"
                )
            else:
                msg = f"User数が{MIN_USERS}よりも少なかったため、メンションはスキップされました。"
            send_instance_notification(msg)
        else:
            logging.info("[INSTANCE] 対象ワールドのインスタンスが存在します。通知は行いません。")
    if 'STATS' in DISCORD_WEBHOOKS:
        send_graph_to_discord(
            DISCORD_WEBHOOKS['STATS'],
            "VRCゲーマーズユーザー統計",
            f"現在のオンラインユーザー数: {online_count}人"
        )
if __name__ == "__main__":
    main()
