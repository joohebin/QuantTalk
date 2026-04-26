"""
邮件发送工具
支持 SendGrid 和 SMTP 两种方式
"""
import smtplib
import random
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import (
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SENDGRID_FROM_NAME,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
)


def generate_code(length: int = 6) -> str:
    """生成随机验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_email_via_smtp(to_email: str, subject: str, html_content: str) -> bool:
    """通过 SMTP 发送邮件（适用于任何邮箱服务）"""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP 未配置，跳过发送")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{SENDGRID_FROM_NAME} <{SMTP_USER}>"
    msg['To'] = to_email
    
    # 纯文本版本
    text_content = html_content.replace('<br>', '\n').replace('<p>', '').replace('</p>', '\n')
    msg.attach(MIMEText(text_content, 'plain'))
    
    # HTML 版本
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"邮件发送成功: {to_email}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


def send_email_via_sendgrid(to_email: str, subject: str, html_content: str) -> bool:
    """通过 SendGrid API 发送邮件"""
    if not SENDGRID_API_KEY:
        print("SendGrid API Key 未配置，尝试 SMTP")
        return send_email_via_smtp(to_email, subject, html_content)
    
    try:
        import requests
        
        data = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": SENDGRID_FROM_EMAIL, "name": SENDGRID_FROM_NAME},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}]
        }
        
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=data,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code in (200, 201, 202):
            print(f"邮件发送成功 (SendGrid): {to_email}")
            return True
        else:
            print(f"SendGrid 发送失败: {response.status_code} {response.text}")
            # 回退到 SMTP
            return send_email_via_smtp(to_email, subject, html_content)
            
    except ImportError:
        print("requests 库未安装，使用 SMTP")
        return send_email_via_smtp(to_email, subject, html_content)
    except Exception as e:
        print(f"SendGrid 发送失败: {e}")
        return send_email_via_smtp(to_email, subject, html_content)


def send_verification_email(to_email: str, code: str, purpose: str = "注册") -> bool:
    """发送验证码邮件"""
    if purpose == "注册":
        subject = "【QuantTalk】注册验证码"
    elif purpose == "登录":
        subject = "【QuantTalk】登录验证码"
    else:
        subject = "【QuantTalk】验证码"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #5865f2, #4752c4); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">QuantTalk</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            <p style="font-size: 16px; color: #333;">您好，</p>
            <p style="font-size: 16px; color: #333;">您的{purpose}验证码是：</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
                <span style="font-size: 32px; font-weight: bold; color: #5865f2; letter-spacing: 8px;">{code}</span>
            </div>
            <p style="font-size: 14px; color: #666;">验证码有效期为 <strong>10 分钟</strong>，请勿将验证码告诉他人。</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #999;">如果您没有发起此请求，请忽略此邮件。</p>
        </div>
    </div>
    """
    
    return send_email_via_sendgrid(to_email, subject, html_content)
