from flask import Flask, render_template, request, flash, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# 環境変数の確認（起動時にログ出力）
print("環境変数確認:")
print(f"GMAIL_USER: {os.environ.get('GMAIL_USER')}")
print(f"GMAIL_PASSWORD設定状況: {'設定済み' if os.environ.get('GMAIL_PASSWORD') else '未設定'}")

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
# アプリケーション設定
# =====================================
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'meeting-scheduler-2025')

# メール設定（環境変数から取得）
SENDER_EMAIL = os.environ.get('GMAIL_USER', 'bizmowa1@gmail.com')
PASSWORD = os.environ.get('GMAIL_PASSWORD', 'your-app-password')
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
    try:
        print("メール送信開始")  # デバッグ用
        print(f"送信元メールアドレス: {SENDER_EMAIL}")  # デバッグ用
        
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

【面談希望】
{form_data.get('meeting_preference', '希望なし')}

【連絡先情報】
企業名: {form_data['company']}
担当者名: {form_data['contact_person']}
メールアドレス: {form_data['email']}

送信日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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

        print("SMTP接続開始")  # デバッグ用
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            try:
                print(f"Gmail認証開始: {SENDER_EMAIL}")  # デバッグ用
                server.login(SENDER_EMAIL, PASSWORD)
                print("Gmail認証成功")  # デバッグ用

                # 管理者への通知メール送信
                for recipient in NOTIFICATION_EMAILS:
                    print(f"管理者宛メール送信開始: {recipient}")  # デバッグ用
                    msg = MIMEMultipart()
                    msg["From"] = SENDER_EMAIL
                    msg["To"] = recipient
                    msg["Subject"] = subject
                    msg.attach(MIMEText(admin_body, "plain"))
                    server.send_message(msg)
                    print(f"管理者宛メール送信成功: {recipient}")

                # 申込者への自動返信メール送信
                print(f"申込者宛メール送信開始: {form_data['email']}")  # デバッグ用
                auto_reply = MIMEMultipart()
                auto_reply["From"] = SENDER_EMAIL
                auto_reply["To"] = form_data['email']
                auto_reply["Subject"] = "面談予約リクエストを受け付けました"
                auto_reply.attach(MIMEText(client_body, "plain"))
                server.send_message(auto_reply)
                print("申込者宛メール送信成功")

                return True

            except smtplib.SMTPAuthenticationError as e:
                print(f"Gmail認証エラー詳細: {str(e)}")  # デバッグ用
                return False
            except Exception as e:
                print(f"メール送信エラー詳細: {str(e)}")  # デバッグ用
                return False

    except Exception as e:
        print(f"予期せぬエラー詳細: {str(e)}")  # デバッグ用
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # フォームデータの取得と検証
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
                'email': request.form['email'],
                'meeting_preference': '面談希望' if request.form.get('meeting_preference') else '希望なし'
            }

            print("フォームデータ:", form_data)  # デバッグ用

            # メール送信処理
            email_result = send_notification_email(form_data)
            print("メール送信結果:", email_result)  # デバッグ用

            if email_result:
                flash('面談予約リクエストを受け付けました。担当者より折り返しご連絡させていただきます。', 'success')
            else:
                flash('送信に失敗しました。しばらく時間をおいて再度お試しください。', 'error')

            return redirect(url_for('index'))

        except Exception as e:
            print(f"予約処理エラー詳細: {str(e)}")  # デバッグ用
            flash('システムエラーが発生しました。', 'error')
            return redirect(url_for('index'))

    return render_template('index.html', company_info=COMPANY_INFO)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)