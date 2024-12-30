from flask import Flask, request, jsonify
import requests
import os
import pynetbox
import requests
import re
import urllib3
import warnings
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
import random


app = Flask(__name__)

TELEGRAM_TOKEN = '2004478698:AAEsHPaCw_mbTsCaxtV2YoTAdmi1cB6N9Rw'  # Thay thế bằng token của bot Telegram của bạn
TELEGRAM_CHAT_ID = '717154123'  # Thay thế bằng chat ID của bạn hoặc nhóm

NetBox_URL = 'https://172.16.99.43/'
NetBox_Token = 'df3f38a9b679c0e99c78fa4cfea1c566f5b06ca2'

def send_telegram_message(message):
    """
    Gửi tin nhắn tới Telegram sử dụng bot API.
    """
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    response = requests.post(url, json=payload)
    return response


def netbox_connection_check(netboxurl, netboxtoken):
    try:
        warnings.simplefilter("ignore", InsecureRequestWarning)  
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            netboxurl,
            headers={"Authorization": f"Token {netboxtoken}"},
            timeout=20,
            verify=False  
        )
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if response.status_code == 200:
            global nb
            nb = pynetbox.api(netboxurl, token=netboxtoken)
            nb.http_session.verify = False  
            print("Connection Check complete!")
        else:
            print(f"Connection Error: {response.status_code} - {response.reason}")
            return None
    except requests.exceptions.SSLError as e:
        print(f"SSL Error: Can't verify SSL certificate. More: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: Unable to reach NetBox. More: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: NetBox did not respond in time. More: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error: An unknown error occurred. More: {e}")
    return None

def nb_rack_get(rack_id):
    rackname = nb.dcim.racks.get(rack_id)
    return rackname

def nb_rack_jounral(rack_id_truoc,rack_name_hien_tai,rack_name_truoc):
    if rack_name_hien_tai == "KHONG CO GIA TRI":
        journal_entry = {
            "assigned_object_type": "dcim.rack",
            "assigned_object_id": rack_id_truoc,
            "kind": "info",
            "comments": f"TB đã được gỡ ra khỏi tủ {rack_name_truoc}",
            # "comments": f"TB chuyen tu {rack_name_truoc} sang {rack_name_hien_tai}",
        }
        print(rack_id_truoc)
        nb.extras.journal_entries.create(journal_entry)

    else: 
        journal_entry = {
            "assigned_object_type": "dcim.rack",
            "assigned_object_id": rack_id_truoc,
            "kind": "info",
            "comments": f"TB chuyen tu {rack_name_truoc} sang {rack_name_hien_tai}",
        }
        nb.extras.journal_entries.create(journal_entry)

def handle_webhook(data):
    """
    Hàm để xử lý dữ liệu webhook nhận được từ NetBox và in ra màn hình.
    """
    netbox_connection_check(NetBox_URL, NetBox_Token)
    print("Webhook received!")
    print(data)

    # Hiển thị chi tiết cập nhật nếu có
    message = "Webhook received!\n"
    if 'event' in data:
        message += f"Event: {data['event']}\t"
    if 'timestamp' in data:
        message += f"Timestamp: {data['timestamp']}\n"

    rack_data = str(data.get('data', {}).get('rack'))
    if rack_data == "None":
        rack_name_hien_tai = "KHONG CO GIA TRI"
        print(rack_name_hien_tai)
        rack_id_truoc = data['snapshots']['prechange']['rack']
        print(rack_id_truoc)
        rack_name_truoc = nb_rack_get(rack_id_truoc)
        message += f"Rack hien tai: {rack_name_hien_tai} \nRack truoc: {rack_name_truoc}\n"
        send_telegram_message(message)  # Gửi thông báo tới Telegram
        nb_rack_jounral(rack_id_truoc,rack_name_hien_tai,rack_name_truoc)
   
    if rack_data != "None":    
        rack_name_hien_tai = data['data']['rack']['name']
        rack_id_truoc = data['snapshots']['prechange']['rack']
        rack_name_truoc = nb_rack_get(rack_id_truoc)
        print(rack_name_truoc)
        print("################################")
        message += f"Rack hien tai: {rack_name_hien_tai} \nRack truoc: {rack_name_truoc}\n"
        send_telegram_message(message)  # Gửi thông báo tới Telegram

        nb_rack_jounral(rack_id_truoc,rack_name_hien_tai,rack_name_truoc)


@app.route('/webhook', methods=['POST'])
def webhook():
    print("Step 1: Checking NetBox connection...")
    netbox_connection_check(NetBox_URL, NetBox_Token)
    
    if request.method == 'POST':
        data = request.json
        handle_webhook(data)  # Gọi hàm handle_webhook và truyền dữ liệu nhận được

        # In thông báo ra màn hình trước khi trả về phản hồi
        response_message = {'message': 'HCD Webhook received!'}
        print(f"Returning response: {response_message}, Status code: 200")

        return jsonify(response_message), 200  # Trả về phản hồi HTTP 200 OK
    else:
        return jsonify({'message': 'Method not allowed'}), 405  # Trả về phản hồi HTTP 405 Method Not Allowed

if __name__ == '__main__':
    app.run("0.0.0.0", port=5000, debug=True)


