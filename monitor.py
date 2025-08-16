import os
    import json
    import gspread
    import requests
    import hashlib
    from datetime import datetime

    # --- Cấu hình ---
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    GCP_CREDS_JSON_STR = os.getenv('GCP_CREDS_JSON')
    SHEET_NAME = "Telegram Bot Links" # Tên Google Sheet của bạn

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
            response = requests.post(url, json=payload)
            print(f"Sent message to {user_id}. Response: {response.json()}")
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")

    # --- Hàm Chính ---
    def main():
        print("Starting monitoring process...")
        try:
            # Xác thực với Google Sheets
            gcp_creds_dict = json.loads(GCP_CREDS_JSON_STR)
            gc = gspread.service_account_from_dict(gcp_creds_dict)
            sh = gc.open(SHEET_NAME).sheet1
            records = sh.get_all_records() # Lấy tất cả dữ liệu
            print(f"Found {len(records)} links to check.")
        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            return

        for idx, row in enumerate(records):
            row_num = idx + 2 # Số hàng trong sheet (bắt đầu từ 2 vì có tiêu đề)
            link = row.get('link')
            user_id = row.get('user_id')
            old_hash = row.get('content_hash')

            if not link or not user_id:
                continue

            print(f"Checking link: {link}")
            try:
                # Lấy nội dung link
                response = requests.get(link, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                current_content = response.text
                
                # Tạo hash mới
                new_hash = hashlib.sha256(current_content.encode('utf-8')).hexdigest()

                # So sánh hash
                if not old_hash: # Nếu là link mới, chỉ cập nhật hash
                    print(f"New link found. Updating hash for {link}")
                    sh.update_cell(row_num, 5, new_hash) # Cột 5 là content_hash
                elif old_hash != new_hash:
                    print(f"CHANGE DETECTED for {link}!")
                    # Gửi thông báo
                    message = f"⚠️ Phát hiện có thay đổi tại link:\n<a href='{link}'>{link}</a>"
                    send_telegram_message(user_id, message)
                    # Cập nhật hash mới
                    sh.update_cell(row_num, 5, new_hash)
                else:
                    print(f"No change for {link}")

            except requests.RequestException as e:
                print(f"Could not fetch {link}. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred for link {link}: {e}")

    if __name__ == "__main__":
        main()
