from flask import Flask, render_template, request, flash, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formatdate
from email import encoders
import os
from datetime import datetime

# =====================================
# 環境変数の確認（起動時にログ出力）
# =====================================
print("環境変数確認:")
print(f"GMAIL_USER: {os.environ.get('GMAIL_USER')}")
print(f"GMAIL_PASSWORD設定状況: {'設定済み' if os.environ.get('GMAIL_PASSWORD') else '未設定'}")

# =====================================
# アプリケーション設定
# =====================================
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'meeting-scheduler-2025')

# セキュリティ設定の追加
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'http'

# メール設定（環境変数から取得）
SENDER_EMAIL = os.environ.get('GMAIL_USER', 'bizmowa1@gmail.com')
PASSWORD = os.environ.get('GMAIL_PASSWORD', 'your-app-password')
NOTIFICATION_EMAILS = ["slazengersnow@gmail.com", "bizmowa@gmail.com"]

# ベースURL設定
BASE_URL = "https://mtg.bizmowa.com"

# =====================================
# メール本文生成関数
# =====================================
def create_email_content(form_data, is_admin=True):
    # BASE_URLの定義を確認
    BASE_URL = "https://mtg.bizmowa.com"  # 必ずhttpsを使用

    if is_admin:
        meeting_link = f"{BASE_URL}/"
        return f"""
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

予約フォームURL: {meeting_link}

送信日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    else:
        return f"""
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

予約フォームURL: {meeting_link}

よろしくお願いいたします。
"""

# =====================================
# メール送信関数
# =====================================
def send_notification_email(form_data):
    """通知メールを送信する関数"""
    try:
        print("メール送信開始")
        
        # 1. クライアント向けメールを作成
        client_body = create_email_content(form_data, is_admin=False)
        auto_reply = MIMEMultipart()
        auto_reply["From"] = SENDER_EMAIL
        auto_reply["To"] = form_data['email']
        auto_reply["Subject"] = "面談予約リクエストを受け付けました"
        auto_reply["Date"] = formatdate(localtime=True)
        auto_reply.attach(MIMEText(client_body, "plain"))

        # 2. 管理者向けメール本文を作成
        admin_body = create_email_content(form_data, is_admin=True)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            try:
                server.login(SENDER_EMAIL, PASSWORD)
                print("Gmail認証成功")

                # 3. クライアントへメール送信
                server.send_message(auto_reply)
                print("申込者宛メール送信成功")

                # 4. 通知メールを作成し、クライアントメールを添付
                for recipient in NOTIFICATION_EMAILS:
                    msg = MIMEMultipart()
                    msg["From"] = SENDER_EMAIL
                    msg["To"] = recipient
                    msg["Subject"] = "新しい面談予約リクエストが届きました"
                    msg["Date"] = formatdate(localtime=True)
                    
                    msg.attach(MIMEText(admin_body, "plain"))
                    
                    attachment = MIMEBase('message', 'rfc822')
                    attachment.set_payload(auto_reply.as_string())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename='client_confirmation_email.eml'
                    )
                    msg.attach(attachment)
                    
                    server.send_message(msg)
                    print(f"通知メール送信成功: {recipient}")

                return True

            except smtplib.SMTPAuthenticationError as e:
                print(f"Gmail認証エラー詳細: {str(e)}")
                return False
            except Exception as e:
                print(f"メール送信エラー詳細: {str(e)}")
                return False

    except Exception as e:
        print(f"予期せぬエラー詳細: {str(e)}")
        return False

# =====================================
# セキュリティミドルウェア 一時的に？Azureでデプロイする時にコメントアウト
# =====================================
#@app.before_request
#def before_request():
#    if not request.is_secure and not app.debug:
#        url = request.url.replace('http://', 'https://', 1)
#        return redirect(url, code=301)

# =====================================
# ルート設定
# =====================================
@app.route('/', methods=['GET', 'POST'])
def index():
    """メインページのルートハンドラ"""
    if request.method == 'POST':
        try:
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

            email_result = send_notification_email(form_data)

            if email_result:
                flash('面談予約リクエストを受け付けました。担当者より折り返しご連絡させていただきます。', 'success')
            else:
                flash('送信に失敗しました。しばらく時間をおいて再度お試しください。', 'error')

            return redirect(url_for('index', _scheme='https'))

        except Exception as e:
            print(f"予約処理エラー詳細: {str(e)}")
            flash('システムエラーが発生しました。', 'error')
            return redirect(url_for('index', _scheme='https'))

    return render_template('index.html')

# =====================================
# アプリケーション起動
# =====================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
    
