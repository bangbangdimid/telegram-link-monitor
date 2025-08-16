import os
import json
import gspread
import requests
import hashlib
from datetime import datetime

# --- Cấu hình ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GCP_CREDS_JSON_STR = os.getenv('GCP_CREDS_JSON')
SHEET_NAME = "Telegram Bot Links"

# --- Hàm Gửi Thông Báo Telegram ---
def send_telegram_message(user_id, message):
    """Gửi tin nhắn tới người dùng cụ thể qua Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status() 
        print(f"Sent message to {user_id}. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {user_id}: {e}")

# --- Hàm Chính ---
def main():
    """Hàm chính thực thi toàn bộ logic giám sát."""
    print("Starting monitoring process...")

    if not TELEGRAM_TOKEN or not GCP_CREDS_JSON_STR:
        print("Error: TELEGRAM_TOKEN or GCP_CREDS_JSON not found in environment variables.")
        return

    try:
        gcp_creds_dict = json.loads(GCP_CREDS_JSON_STR)
        gc = gspread.service_account_from_dict(gcp_creds_dict)
        sh = gc.open(SHEET_NAME).sheet1
        records = sh.get_all_records()
        print(f"Found {len(records)} links to check.")
    except Exception as e:
        print(f"Fatal Error: Could not connect to Google Sheets. Reason: {e}")
        return 

    for idx, row in enumerate(records):
        row_num = idx + 2  
        link = row.get('link')
        user_id = row.get('user_id')
        old_hash = row.get('content_hash')

        if not link or not user_id:
            print(f"Skipping row {row_num} due to missing link or user_id.")
            continue

        print(f"Checking link: {link}")
        
        # --- KHỐI TRY...EXCEPT BẮT ĐẦU TỪ ĐÂY ---
        # 'try' và 'except' phải nằm cùng một cấp, thụt vào bên trong vòng lặp 'for'
        try:
            # Nội dung bên trong 'try' phải thụt vào sâu hơn một cấp
            response = requests.get(link, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            current_content = response.text
            
            new_hash = hashlib.sha256(current_content.encode('utf-8', 'ignore')).hexdigest()

            if not old_hash:
                print(f"New link found. Updating hash for {link}")
                sh.update_cell(row_num, 5, new_hash)
            elif old_hash != new_hash:
                print(f"CHANGE DETECTED for {link}!")
                message = f"⚠️ Phát hiện có thay đổi tại link:\n<a href='{link}'>{link}</a>"
                send_telegram_message(user_id, message)
                sh.update_cell(row_num, 5, new_hash)
            else:
                print(f"No change for {link}")

        except requests.RequestException as e:
            # Khối 'except' này thẳng hàng với 'try' ở trên
            print(f"Could not fetch {link}. Error: {e}")
        except Exception as e:
            # Khối 'except' này cũng thẳng hàng với 'try'
            print(f"An unexpected error occurred for link {link}: {e}")
    
    print("Monitoring process finished.")

# --- Điểm bắt đầu chạy script ---
if __name__ == "__main__":
    main()
