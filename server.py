import json
import logging
import os
import re
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DONORS_PATH = BASE_DIR / "donors.json"
ENV_PATH = BASE_DIR / ".env"
LOG_PATH = BASE_DIR / "aligo_sms.log"
ALIGO_SEND_MASS_URL = "https://apis.aligo.in/send_mass/"
MAX_MASS_RECIPIENTS = 500
SMS_BYTE_LIMIT = 90

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def load_env_file(path):
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def normalize_phone(value):
    digits = re.sub(r"\D", "", str(value))
    if not re.fullmatch(r"01\d{8,9}", digits):
        raise ValueError("Invalid Korean mobile phone number")
    return digits


def sanitize_sms_text(value):
    text = str(value)
    text = text.replace("🎉", "").replace("🎁", "").replace("🎂", "")
    return text.encode("euc-kr", errors="replace").decode("euc-kr")


def euc_kr_size(value):
    return len(value.encode("euc-kr", errors="replace"))


def get_message_type(messages):
    max_size = max(euc_kr_size(message) for message in messages)
    return "SMS" if max_size <= SMS_BYTE_LIMIT else "LMS"


def load_donors_by_id():
    with DONORS_PATH.open("r", encoding="utf-8") as file:
        donors = json.load(file)
    return {donor["donor_id"]: donor for donor in donors}


def build_birthday_message(name, template_id):
    templates = {
        "1": (
            "{name} 후원자님께\n\n"
            "후원자님의 따뜻한 동행 덕분에 세상이 더욱 밝아집니다. "
            "뜻깊은 생일을 진심으로 축하드리며, 오늘 하루 행복이 가득하시기를 바랍니다.\n\n"
            "- 행복복지재단 -"
        ),
        "2": (
            "{name} 후원자님께\n\n"
            "나눔을 실천해 주시는 아름다운 마음이 바로 오늘의 주인공입니다. "
            "후원자님의 특별한 날을 진심으로 기념하며, 생일을 축하드립니다.\n\n"
            "- 행복복지재단 -"
        ),
        "3": (
            "{name} 후원자님께\n\n"
            "생일을 진심으로 축하드립니다! 언제나 아낌없는 성원을 보내주셔서 감사드리며, "
            "즐겁고 기쁨 가득한 생일날 보내시길 기원합니다.\n\n"
            "- 행복복지재단 -"
        ),
    }
    return sanitize_sms_text(templates.get(str(template_id), templates["1"]).format(name=name))


def post_form(url, payload):
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def send_birthday_sms(donor_ids, template_id):
    if not donor_ids:
        raise ValueError("No donor IDs provided")
    if len(donor_ids) > MAX_MASS_RECIPIENTS:
        raise ValueError(f"Cannot send more than {MAX_MASS_RECIPIENTS} recipients at once")

    api_key = get_required_env("ALIGO_API_KEY")
    user_id = get_required_env("ALIGO_USER_ID")
    sender = get_required_env("ALIGO_SENDER")
    testmode_yn = os.environ.get("ALIGO_TESTMODE_YN", "Y").strip().upper() or "Y"

    donors_by_id = load_donors_by_id()
    selected_donors = []
    for donor_id in donor_ids:
        donor = donors_by_id.get(str(donor_id))
        if not donor:
            raise ValueError(f"Unknown donor ID: {donor_id}")
        selected_donors.append(donor)

    messages = [build_birthday_message(donor["name"], template_id) for donor in selected_donors]
    msg_type = get_message_type(messages)
    payload = {
        "key": api_key,
        "user_id": user_id,
        "sender": sender,
        "cnt": str(len(selected_donors)),
        "msg_type": msg_type,
        "testmode_yn": testmode_yn,
    }
    if msg_type == "LMS":
        payload["title"] = "생일을 축하드립니다"

    for index, donor in enumerate(selected_donors, start=1):
        payload[f"rec_{index}"] = normalize_phone(donor["phone"])
        payload[f"msg_{index}"] = messages[index - 1]

    result = post_form(ALIGO_SEND_MASS_URL, payload)
    result_code = int(result.get("result_code", 0))
    safe_result = {
        "result_code": result_code,
        "message": result.get("message", ""),
        "msg_id": result.get("msg_id"),
        "success_cnt": result.get("success_cnt", 0),
        "error_cnt": result.get("error_cnt", 0),
        "msg_type": result.get("msg_type", msg_type),
        "testmode_yn": testmode_yn,
    }

    if result_code == 1:
        logging.info(
            "ALIGO birthday SMS success msg_id=%s count=%s msg_type=%s testmode=%s",
            safe_result["msg_id"],
            len(selected_donors),
            safe_result["msg_type"],
            testmode_yn,
        )
    else:
        logging.error(
            "ALIGO birthday SMS failed result_code=%s message=%s count=%s",
            result_code,
            safe_result["message"],
            len(selected_donors),
        )
    return safe_result


class DashboardHandler(SimpleHTTPRequestHandler):
    blocked_filenames = {"aligo_sms.log"}

    def _is_blocked_static_path(self):
        request_path = urllib.parse.urlparse(self.path).path
        parts = Path(urllib.parse.unquote(request_path)).parts
        return any(part.startswith(".") for part in parts if part not in {"/", "."}) or any(
            part in self.blocked_filenames for part in parts
        )

    def do_GET(self):
        if self._is_blocked_static_path():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        super().do_GET()

    def do_HEAD(self):
        if self._is_blocked_static_path():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        super().do_HEAD()

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/birthday-sms":
            self._send_json(404, {"ok": False, "message": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            request_body = json.loads(raw_body or "{}")
            donor_ids = request_body.get("donor_ids", [])
            template_id = request_body.get("template_id", "1")
            result = send_birthday_sms(donor_ids, template_id)
            if result["result_code"] == 1:
                self._send_json(200, {"ok": True, "result": result})
            else:
                self._send_json(502, {"ok": False, "result": result})
        except RuntimeError as error:
            logging.error("ALIGO configuration error: %s", error)
            self._send_json(500, {"ok": False, "message": str(error)})
        except ValueError as error:
            logging.warning("Bad birthday SMS request: %s", error)
            self._send_json(400, {"ok": False, "message": str(error)})
        except Exception as error:
            logging.exception("Unexpected birthday SMS error")
            self._send_json(500, {"ok": False, "message": "문자 발송 중 서버 오류가 발생했습니다."})


def run():
    load_env_file(ENV_PATH)
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("", port), DashboardHandler)
    print(f"HeartShare dashboard server running at http://localhost:{port}")
    print("ALIGO_TESTMODE_YN defaults to Y. Set ALIGO_TESTMODE_YN=N only for live sending.")
    server.serve_forever()


if __name__ == "__main__":
    run()
