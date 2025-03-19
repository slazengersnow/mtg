import os
import smtplib
import ssl
from flask import Flask, render_template, request, flash, redirect, url_for
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate, formataddr
from datetime import datetime
import logging
from pathlib import Path
import tempfile

# =====================================
# ロギング設定
# =====================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# アプリケーション設定
# =====================================
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'meeting-scheduler-2025')

# セキュリティ設定
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'https'

# メール設定
SENDER_EMAIL = os.environ.get('MAIL_USER', 'info1@bizmowa.com')
SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'Bizmowa予約システム')
PASSWORD = os.environ.get('MAIL_PASSWORD', '')

# 管理者メールアドレス
NOTIFICATION_EMAILS = [
    "y.inoue@filterbank.co.jp", 
    "bizmowa@gmail.com"
]

# ベースURL設定 - 環境変数 > 独自ドメイン > Renderのデフォルト
BASE_URL = os.environ.get('BASE_URL', "https://mtg.bizmowa.com")

# 添付ファイルディレクトリ
ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attachments')

# 環境変数の確認（起動時にログ出力）
logger.info("環境変数確認:")
logger.info(f"MAIL_USER: {SENDER_EMAIL}")
logger.info(f"BASE_URL: {BASE_URL}")
logger.info(f"添付ファイルディレクトリ: {ATTACHMENTS_DIR}")

# 添付ファイルディレクトリの存在確認
if not os.path.exists(ATTACHMENTS_DIR):
    try:
        os.makedirs(ATTACHMENTS_DIR)
        logger.info(f"添付ファイルディレクトリを作成しました: {ATTACHMENTS_DIR}")
    except Exception as e:
        logger.error(f"添付ファイルディレクトリの作成に失敗しました: {str(e)}")

# =====================================
# セキュリティヘッダー
# =====================================
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

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

【面談希望】
{form_data.get('meeting_preference', '希望なし')}

予約フォームURL: {meeting_link}

※申込内容の詳細をテキストファイルで添付しております。
 こちらでご確認いただけます。

よろしくお願いいたします。
"""

# =====================================
# 申込内容のテキストファイルを作成する関数
# =====================================
def create_application_text_file(form_data):
    """申込内容を含むテキストファイルを作成してパスを返す"""
    try:
        # 一時ファイルのパスを生成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"お申し込み内容_{form_data['company']}_{timestamp}.txt"
        file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # メール内容をテキストで作成
        email_content = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
面談申し込み内容 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{form_data['company']} {form_data['contact_person']}様

面談予約フォームにお問い合わせいただき、ありがとうございます。
以下の内容でご予約を承りました。

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

【予約フォームURL】
{BASE_URL}

担当者より2、3営業日以内に折り返しご連絡させていただきます。
よろしくお願いいたします。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bizmowa予約システム
Email: {SENDER_EMAIL}
URL: {BASE_URL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # テキストファイルとして保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(email_content)
            
        logger.info(f"テキストファイルを作成しました: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"テキストファイル作成エラー: {str(e)}")
        return None

# =====================================
# 添付ファイル取得関数
# =====================================
def get_attachment_files():
    """添付ファイルディレクトリから送信すべきファイルのリストを取得"""
    try:
        attachment_files = []
        if os.path.exists(ATTACHMENTS_DIR):
            for file in os.listdir(ATTACHMENTS_DIR):
                file_path = os.path.join(ATTACHMENTS_DIR, file)
                if os.path.isfile(file_path):
                    attachment_files.append(file_path)
            logger.info(f"添付ファイルを{len(attachment_files)}件見つけました")
        return attachment_files
    except Exception as e:
        logger.error(f"添付ファイル取得エラー: {str(e)}")
        return []

# =====================================
# PDF版申込書を作成する関数（オプション）
# =====================================
def create_application_pdf(form_data):
    """
    申込内容をPDFで作成する（依存ライブラリが必要なためオプション）
    実際に使用する場合は、reportlabなどのライブラリを追加してください
    """
    # PDFライブラリがインストールされている場合のみ動作
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 一時ファイルのパスを生成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"お申し込み内容_{form_data['company']}_{timestamp}.pdf"
        file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # 日本語フォントの登録（必要に応じて）
        try:
            pdfmetrics.registerFont(TTFont('IPAGothic', '/usr/share/fonts/ipa-gothic/ipag.ttf'))
            font_name = 'IPAGothic'
        except:
            font_name = 'Helvetica'
        
        # PDFドキュメント設定
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # タイトル
        title = Paragraph(f"面談申し込み内容 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # 本文
        content = f"""
{form_data['company']} {form_data['contact_person']}様

面談予約フォームにお問い合わせいただき、ありがとうございます。
以下の内容でご予約を承りました。

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

【予約フォームURL】
{BASE_URL}

担当者より2、3営業日以内に折り返しご連絡させていただきます。
よろしくお願いいたします。
"""
        body = Paragraph(content.replace('\n', '<br/>'), styles['Normal'])
        elements.append(body)
        
        # PDFの生成
        doc.build(elements)
        logger.info(f"PDFファイルを作成しました: {file_path}")
        return file_path
    except ImportError:
        logger.warning("reportlabライブラリがインストールされていないため、PDFは作成しません")
        return None
    except Exception as e:
        logger.error(f"PDF作成エラー: {str(e)}")
        return None

# =====================================
# メール送信関数
# =====================================
def send_notification_email(form_data):
    if not SENDER_EMAIL or not PASSWORD:
        logger.error("メール送信設定が不足しています。MAIL_USER、MAIL_PASSWORDを設定してください。")
        return False

    try:
        logger.info("メール送信開始")
        
        # 添付ファイルのリストを取得
        attachment_files = get_attachment_files()
        
        # 申込内容をテキストファイルとして保存
        text_file = create_application_text_file(form_data)
        
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
                client_msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))
                client_msg["To"] = form_data['email']
                client_msg["Subject"] = "面談予約リクエストを受け付けました"
                client_msg["Date"] = formatdate(localtime=True)
                client_msg.attach(MIMEText(create_email_content(form_data, is_admin=False), "plain", "utf-8"))

                # 申込内容のテキストファイルを添付
                if text_file and os.path.exists(text_file):
                    try:
                        with open(text_file, "rb") as attachment:
                            filename = os.path.basename(text_file)
                            part = MIMEApplication(attachment.read(), Name=filename)
                            part['Content-Disposition'] = f'attachment; filename="{filename}"'
                            client_msg.attach(part)
                            logger.info(f"テキストファイルを添付しました: {filename}")
                    except Exception as file_error:
                        logger.error(f"テキストファイル添付エラー: {str(file_error)}")
                
                # 通常の添付ファイルの追加
                for attachment_file in attachment_files:
                    try:
                        with open(attachment_file, "rb") as attachment:
                            filename = os.path.basename(attachment_file)
                            part = MIMEApplication(attachment.read(), Name=filename)
                            part['Content-Disposition'] = f'attachment; filename="{filename}"'
                            client_msg.attach(part)
                            logger.info(f"添付ファイル追加成功: {filename}")
                    except Exception as file_error:
                        logger.error(f"添付ファイル追加エラー ({attachment_file}): {str(file_error)}")

                # クライアントメール送信
                server.send_message(client_msg)
                logger.info("申込者宛メール送信成功")

                # 管理者通知メール送信
                for recipient in NOTIFICATION_EMAILS:
                    recipient = recipient.strip()
                    if not recipient:
                        continue
                        
                    try:
                        admin_msg = MIMEMultipart()
                        admin_msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))
                        admin_msg["To"] = recipient
                        admin_msg["Subject"] = "新しい面談予約リクエストが届きました"
                        admin_msg["Date"] = formatdate(localtime=True)
                        admin_msg.attach(MIMEText(create_email_content(form_data, is_admin=True), "plain", "utf-8"))

                        # 管理者メールにも申込内容ファイルを添付
                        if text_file and os.path.exists(text_file):
                            with open(text_file, "rb") as attachment:
                                filename = os.path.basename(text_file)
                                part = MIMEApplication(attachment.read(), Name=filename)
                                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                                admin_msg.attach(part)

                        server.send_message(admin_msg)
                        logger.info(f"管理者通知メール送信成功: {recipient}")
                    except Exception as recipient_error:
                        logger.error(f"管理者通知メール送信失敗 ({recipient}): {str(recipient_error)}")

                # 一時ファイルの削除
                if text_file and os.path.exists(text_file):
                    try:
                        os.remove(text_file)
                        logger.info(f"一時ファイルを削除しました: {text_file}")
                    except Exception as e:
                        logger.warning(f"一時ファイル削除エラー: {str(e)}")

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
                'meeting_preference': 'オンライン面談希望' if request.form.get('meeting_preference') else '対面希望'
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
    """ヘルスチェック用エンドポイント"""
    return "OK", 200

# =====================================
# アプリケーション起動
# =====================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)