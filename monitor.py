import os
import json
import gspread
import requests
import hashlib
from datetime import datetime

# --- Cấu hình ---
# Lấy thông tin nhạy cảm từ GitHub Secrets
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GCP_CREDS_JSON_STR = os.getenv('GCP_CREDS_JSON')
SHEET_NAME = "Telegram Bot Links" # Đảm bảo tên này khớp với tên Google Sheet của bạn

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
        # Kiểm tra xem Telegram API có trả về lỗi không
        response.raise_for_status() 
        print(f"Sent message to {user_id}. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {user_id}: {e}")

# --- Hàm Chính ---
def main():
    """Hàm chính thực thi toàn bộ logic giám sát."""
    print("Starting monitoring process...")

    # Kiểm tra xem các biến môi trường đã được thiết lập chưa
    if not TELEGRAM_TOKEN or not GCP_CREDS_JSON_STR:
        print("Error: TELEGRAM_TOKEN or GCP_CREDS_JSON not found in environment variables.")
        return

    try:
        # Xác thực với Google Sheets
        gcp_creds_dict = json.loads(GCP_CREDS_JSON_STR)
        gc = gspread.service_account_from_dict(gcp_creds_dict)
        sh = gc.open(SHEET_NAME).sheet1
        records = sh.get_all_records()  # Lấy tất cả dữ liệu
        print(f"Found {len(records)} links to check.")
    except Exception as e:
        print(f"Fatal Error: Could not connect to Google Sheets. Reason: {e}")
        # Nếu không kết nối được sheet thì không cần chạy tiếp
        return 

    # Lặp qua từng hàng trong sheet để kiểm tra
    for idx, row in enumerate(records):
        # row_num là số thứ tự hàng trong sheet, +2 vì hàng 1 là tiêu đề và index bắt đầu từ 0
        row_num = idx + 2  
        link = row.get('link')
        user_id = row.get('user_id')
        old_hash = row.get('content_hash')

        # Bỏ qua nếu hàng thiếu thông tin link hoặc user_id
        if not link or not user_id:
            print(f"Skipping row {row_num} due to missing link or user_id.")
            continue

        print(f"Checking link: {link}")
        try:
            # Tải nội dung của link
            response = requests.get(link, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()  # Báo lỗi nếu status code là 4xx hoặc 5xx
            current_content = response.text
            
            # Tạo hash mới từ nội dung vừa tải
            new_hash = hashlib.sha256(current_content.encode('utf-8', 'ignore')).hexdigest()

            # So sánh hash
            if not old_hash:  # Nếu là link mới, chỉ cập nhật hash
                print(f"New link found. Updating hash for {link}")
                sh.update_cell(row_num, 5, new_hash)  # Cột 5 là cột 'content_hash'
            elif old_hash != new_hash:
                print(f"CHANGE DETECTED for {link}!")
                # Gửi thông báo
                message = f"⚠️ Phát hiện có thay đổi tại link:\n<a href='{link}'>{link}</a>"
                send_telegram_message(user_id, message)
                # Cập nhật lại hash mới để không thông báo lại
                sh.update_cell(row_num, 5, new_hash)
            else:
                print(f"No change for {link}")

        except requests.RequestException as e:
            # Lỗi khi tải link (VD: 404 Not Found, 500 Server Error, timeout)
            print(f"Could not fetch {link}. Error: {e}")
        except Exception as e:
            # Các lỗi không lường trước khác
            print(f"An unexpected error occurred for link {link}: {e}")
    
    print("Monitoring process finished.")

# --- Điểm bắt đầu chạy script ---
# Cấu trúc này đảm bảo rằng hàm main() sẽ được gọi khi bạn chạy file python
if __name__ == "__main__":
    main()
            except requests.RequestException as e:
                print(f"Could not fetch {link}. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred for link {link}: {e}")

    if __name__ == "__main__":
        main()
