import os
import smtplib
import ssl
from flask import Flask, render_template, request, flash, redirect, url_for
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from datetime import datetime
import logging

# =====================================
# ロギング設定
# =====================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# 環境変数の確認（起動時にログ出力）
# =====================================
logger.info("環境変数確認:")
logger.info(f"MAIL_USER: {os.environ.get('MAIL_USER')}")
logger.info(f"MAIL_PASSWORD設定状況: {'設定済み' if os.environ.get('MAIL_PASSWORD') else '未設定'}")
logger.info(f"BASE_URL: {os.environ.get('BASE_URL')}")

# =====================================
# アプリケーション設定
# =====================================
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'meeting-scheduler-2025')

# セキュリティ設定の追加
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'https'

# メール設定（環境変数から取得）
SENDER_EMAIL = os.environ.get('MAIL_USER', '')
PASSWORD = os.environ.get('MAIL_PASSWORD', '')

# 管理者メール
NOTIFICATION_EMAILS = os.environ.get('ADMIN_EMAILS', 'slazengersnow@gmail.com,bizmowa@gmail.com').split(',')

# ベースURL設定
BASE_URL = os.environ.get('BASE_URL', "https://bizmowa-mtg-jp.an.r.appspot.com")

# =====================================
# メール本文生成関数
# =====================================
def create_email_content(form_data, is_admin=True):
    meeting_link = BASE_URL

    if is_admin:
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
    if not SENDER_EMAIL or not PASSWORD:
        logger.error("メール送信設定が不足しています。MAIL_USER、MAIL_PASSWORDを設定してください。")
        return False

    try:
        logger.info("メール送信開始")
        
        # エックスサーバー SMTP設定
        smtp_server = "sv1216.xserver.jp"
        smtp_port = 465  # SSL/TLS port

        # SSL/TLSコンテキストを作成
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            try:
                # SMTP認証
                server.login(SENDER_EMAIL, PASSWORD)
                logger.info("SMTP認証成功")

                # クライアントメール作成
                client_msg = MIMEMultipart()
                client_msg["From"] = SENDER_EMAIL
                client_msg["To"] = form_data['email']
                client_msg["Subject"] = "面談予約リクエストを受け付けました"
                client_msg["Date"] = formatdate(localtime=True)
                client_msg.attach(MIMEText(create_email_content(form_data, is_admin=False), "plain"))

                # クライアントメール送信
                server.send_message(client_msg)
                logger.info("申込者宛メール送信成功")

                # 管理者通知メール送信
                for recipient in NOTIFICATION_EMAILS:
                    recipient = recipient.strip()  # 空白を削除
                    if not recipient:
                        continue
                        
                    try:
                        admin_msg = MIMEMultipart()
                        admin_msg["From"] = SENDER_EMAIL
                        admin_msg["To"] = recipient
                        admin_msg["Subject"] = "新しい面談予約リクエストが届きました"
                        admin_msg["Date"] = formatdate(localtime=True)
                        admin_msg.attach(MIMEText(create_email_content(form_data, is_admin=True), "plain"))

                        server.send_message(admin_msg)
                        logger.info(f"管理者通知メール送信成功: {recipient}")
                    except Exception as recipient_error:
                        logger.error(f"管理者通知メール送信失敗 ({recipient}): {str(recipient_error)}")

                return True

            except smtplib.SMTPAuthenticationError as auth_error:
                logger.error(f"SMTP認証エラー: {str(auth_error)}")
                return False
            except Exception as send_error:
                logger.error(f"メール送信エラー詳細: {str(send_error)}")
                return False

    except Exception as e:
        logger.error(f"予期せぬエラー詳細: {str(e)}")
        return False

# =====================================
# ルート設定
# =====================================
@app.route('/', methods=['GET', 'POST'])
def index():
    """メインページのルートハンドラ"""
    if request.method == 'POST':
        try:
            logger.info("フォーム送信を受信")
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

            logger.info(f"送信フォームデータ: {form_data}")
            email_result = send_notification_email(form_data)

            if email_result:
                flash('面談予約リクエストを受け付けました。担当者より折り返しご連絡させていただきます。', 'success')
                logger.info("メール送信成功、フラッシュメッセージを設定")
            else:
                flash('送信に失敗しました。しばらく時間をおいて再度お試しください。', 'error')
                logger.error("メール送信失敗、エラーメッセージを設定")

            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"予約処理エラー詳細: {str(e)}")
            flash('システムエラーが発生しました。', 'error')
            return redirect(url_for('index'))

    return render_template('index.html')

# =====================================
# ヘルスチェックエンドポイント
# =====================================
@app.route('/health', methods=['GET'])
def health_check():
    """GCPのヘルスチェック用エンドポイント"""
    return "OK", 200

# =====================================
# アプリケーション起動
# =====================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)