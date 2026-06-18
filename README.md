# HeartShare 후원자 대시보드

복지 기관 후원자 관리 자동화 MVP입니다. 정적 대시보드와 알리고 생일 축하 문자 발송용 Python 백엔드를 함께 사용합니다.

## 실행

1. 환경변수 파일을 준비합니다.

```bash
cp .env.example .env
```

2. `.env`에 알리고 인증 정보를 입력합니다.

```bash
ALIGO_API_KEY=발급받은_API_KEY
ALIGO_USER_ID=알리고_가입_아이디
ALIGO_SENDER=사이트에_사전등록한_발신번호
ALIGO_TESTMODE_YN=Y
PORT=8000
```

3. 대시보드 서버를 실행합니다.

```bash
python3 server.py
```

4. 브라우저에서 `http://localhost:8000`을 엽니다.

## 문자 발송

- 프론트엔드는 `/api/birthday-sms`에 후원자 ID와 템플릿 ID만 전송합니다.
- 알리고 API Key, 사용자 ID, 발신번호는 서버의 환경변수에서만 읽습니다.
- 기본값은 `ALIGO_TESTMODE_YN=Y`이며 실제 과금/발송 없이 연동을 검증합니다.
- 실제 발송 전에는 알리고 사이트에서 발신번호 등록을 완료하고, `.env`에서 `ALIGO_TESTMODE_YN=N`으로 변경합니다.
- 발송 결과와 실패 사유는 `aligo_sms.log`에 기록됩니다.
