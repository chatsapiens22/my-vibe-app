import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 설정 정보
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DONORS_FILE = os.path.join(PROJECT_DIR, 'donors.json')
TEMPLATE_FILE = os.path.join(PROJECT_DIR, 'welfare_newsletter.html')
LOG_FILE = os.path.join(PROJECT_DIR, 'newsletter_send.log')

# SMTP 환경 변수 로드 (API 키 하드코딩 금지 규칙 준수)
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = os.environ.get('SMTP_PORT', '587')
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'newsletter@bitgoeul.or.kr')

def log_message(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)
    print(message)

def send_email(to_email, to_name, html_content):
    # 이메일 메시지 생성
    msg = MIMEMultipart('alternative')
    msg['Subject'] = '[빛고을 복지관] 2026 국내외 복지 정책 및 소식 뉴스레터'
    msg['From'] = f"빛고을사회복지관 <{SENDER_EMAIL}>"
    msg['To'] = f"{to_name} <{to_email}>"
    
    # 본문 추가
    msg.attach(MIMEText(html_content, 'html'))
    
    # SMTP 정보가 없으면 시뮬레이션 모드로 동작
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD]):
        log_message(f"[시뮬레이션] 발송 성공 -> 수신자: {to_name}({to_email})")
        return True

    try:
        # 실제 메일 발송 처리
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        log_message(f"[실제 발송] 성공 -> 수신자: {to_name}({to_email})")
        return True
    except Exception as e:
        log_message(f"[실제 발송] 실패 -> 수신자: {to_name}({to_email}), 에러: {str(e)}")
        return False

def main():
    log_message("뉴스레터 정기 발송 배치를 시작합니다.")
    
    # 1. 후원자 리스트 읽기
    if not os.path.exists(DONORS_FILE):
        log_message(f"에러: 후원자 데이터 파일({DONORS_FILE})이 존재하지 않습니다.")
        return
        
    with open(DONORS_FILE, 'r', encoding='utf-8') as f:
        donors = json.load(f)
        
    # 2. 뉴스레터 템플릿 읽기
    if not os.path.exists(TEMPLATE_FILE):
        log_message(f"에러: 뉴스레터 템플릿 파일({TEMPLATE_FILE})이 존재하지 않습니다.")
        return
        
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # 3. 템플릿 내 상대 경로 이미지를 시뮬레이션을 위해 유지하거나 절대 경로로 가이드
    # 실제 발송 시에는 외부 업로드 URL로 치환하여 발송하는 것이 좋습니다.
    
    # 4. 발송 타겟 대상자 필터링 (완료 상태인 후원자 등 - 여기서는 전체 순회 및 상위 5명 샘플 발송 테스트 후 시뮬레이션 완료)
    target_donors = [d for d in donors if d.get('status') == '완료']
    
    # 테스트 과부하를 막기 위해 실거래 연동 전에는 상위 10명 발송 시뮬레이션
    limit = 10
    sent_count = 0
    
    for donor in target_donors[:limit]:
        name = donor.get('name')
        email = donor.get('email')
        if email:
            if send_email(email, name, html_content):
                sent_count += 1
                
    log_message(f"뉴스레터 정기 발송 배치가 완료되었습니다. (성공: {sent_count}/{min(len(target_donors), limit)} 가구)")

if __name__ == '__main__':
    main()
