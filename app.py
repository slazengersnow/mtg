from flask import Flask, render_template, request, flash, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =====================================
# 企業情報設定 (ここを編集してください)
# =====================================
COMPANY_INFO = {
    'name': 'フィルターバンク株式会社',    # 企業名
    'email': 'bizmowa@gmail.com',        # 連絡用メールアドレス
    'phone': '03-XXXX-XXXX',            # 電話番号
    'contact_person': '後藤 広明'         # 担当者名
}

# =====================================
# メール送信設定
# =====================================
app = Flask(__name__)
app.secret_key = 'meeting-scheduler-2025'

# Gmail設定
SENDER_EMAIL = "bizmowa1@gmail.com"
PASSWORD = "zpgq silh txob xzaw"
NOTIFICATION_EMAILS = ["slazengersnow@gmail.com", "bizmowa@gmail.com"]

def create_email_signature():
    """メールの署名を作成"""
    signature_parts = []
    if COMPANY_INFO['name']:
        signature_parts.append(COMPANY_INFO['name'])
    if COMPANY_INFO['contact_person']:
        signature_parts.append(COMPANY_INFO['contact_person'])
    if COMPANY_INFO['email']:
        signature_parts.append(f"Email: {COMPANY_INFO['email']}")
    if COMPANY_INFO['phone']:
        signature_parts.append(f"Tel: {COMPANY_INFO['phone']}")
    
    return "\n".join(signature_parts) if signature_parts else ""

def send_notification_email(form_data):
    """通知メールを送信する"""
    subject = "新しい面談予約リクエストが届きました"
    
    # 管理者向けメール本文
    admin_body = f"""
新しい面談予約リクエストが届きました。

【希望日時】
第1希望: {form_data['date1']} {form_data['time1']}
第2希望: {form_data.get('date2', '')} {form_data.get('time2', '')}
第3希望: {form_data.get('date3', '')} {form_data.get('time3', '')}
第4希望: {form_data.get('date4', '')} {form_data.get('time4', '')}
第5希望: {form_data.get('date5', '')} {form_data.get('time5', '')}

【連絡先情報】
企業名: {form_data['company']}
担当者名: {form_data['contact_person']}
メールアドレス: {form_data['email']}
"""

    # クライアント向けメール本文
    client_body = f"""
{form_data['company']} {form_data['contact_person']}様

面談予約フォームにお問い合わせいただき、ありがとうございます。
担当者より2、3営業日以内に折り返しご連絡させていただきます。

【ご予約内容】
希望日時：
第1希望: {form_data['date1']} {form_data['time1']}
第2希望: {form_data.get('date2', '')} {form_data.get('time2', '')}
第3希望: {form_data.get('date3', '')} {form_data.get('time3', '')}
第4希望: {form_data.get('date4', '')} {form_data.get('time4', '')}
第5希望: {form_data.get('date5', '')} {form_data.get('time5', '')}

よろしくお願いいたします。

"""
    # 署名を追加（企業情報が設定されている場合のみ）
    signature = create_email_signature()
    if signature:
        client_body += f"\n{signature}"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, PASSWORD)
            
            # 管理者への通知
            for recipient in NOTIFICATION_EMAILS:
                msg = MIMEMultipart()
                msg["From"] = SENDER_EMAIL
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(admin_body, "plain"))
                server.send_message(msg)
            
            # 申込者への自動返信
            auto_reply = MIMEMultipart()
            auto_reply["From"] = SENDER_EMAIL
            auto_reply["To"] = form_data['email']
            auto_reply["Subject"] = "面談予約リクエストを受け付けました"
            auto_reply.attach(MIMEText(client_body, "plain"))
            server.send_message(auto_reply)
        
        return True
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_data = {
            'date1': request.form['date1'],
            'time1': request.form['time1'],
            'date2': request.form.get('date2', ''),
            'time2': request.form.get('time2', ''),
            'date3': request.form.get('date3', ''),
            'time3': request.form.get('time3', ''),
            'date4': request.form.get('date4', ''),
            'time4': request.form.get('time4', ''),
            'date5': request.form.get('date5', ''),
            'time5': request.form.get('time5', ''),
            'company': request.form['company'],
            'contact_person': request.form['contact_person'],
            'email': request.form['email']
        }
        
        if send_notification_email(form_data):
            flash('面談予約リクエストを受け付けました。担当者より折り返しご連絡させていただきます。', 'success')
            return redirect(url_for('index'))
        else:
            flash('送信に失敗しました。しばらく時間をおいて再度お試しください。', 'error')

    return render_template('index.html', company_info=COMPANY_INFO)

if __name__ == '__main__':
    app.run(debug=True)