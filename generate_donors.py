import random
import json
import csv
import re
import os
from datetime import datetime, timedelta

# 한국어 이름 조합용 데이터
LAST_NAMES = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '전', '홍']
FIRST_NAME_CHARS = '민서준예지현우아도하윤은채태준민수진희원영성재경훈민동철성호지훈선영은주성민혜진미경'

def generate_korean_name():
    last = random.choice(LAST_NAMES)
    name_len = random.choice([2, 2, 2, 1])  # 2글자 이름 비율을 높게 설정
    first = "".join(random.choices(FIRST_NAME_CHARS, k=name_len))
    return last + first

def generate_phone():
    middle = f"{random.randint(1000, 9999)}"
    last = f"{random.randint(1000, 9999)}"
    return f"010-{middle}-{last}"

def generate_email(name):
    english_last = {
        '김': 'kim', '이': 'lee', '박': 'park', '최': 'choi', '정': 'jung',
        '강': 'kang', '조': 'cho', '윤': 'yoon', '장': 'jang', '임': 'lim',
        '한': 'han', '오': 'oh', '서': 'seo', '신': 'shin', '권': 'kwon',
        '황': 'hwang', '안': 'ahn', '송': 'song', '전': 'jeon', '홍': 'hong'
    }
    last_char = name[0]
    last_eng = english_last.get(last_char, 'user')
    rand_num = random.randint(10, 9999)
    domain = random.choice(['gmail.com', 'naver.com', 'daum.net', 'hanmail.net', 'nate.com'])
    return f"{last_eng}{rand_num}@{domain}"

def generate_birthday():
    # 20대(2006년생) ~ 70대(1956년생)
    start_date = datetime(1956, 1, 1)
    end_date = datetime(2006, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date.strftime('%Y-%m-%d')

def generate_join_date():
    # 최근 3년 (2023-01-01 ~ 2026-06-18)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2026, 6, 18)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date.strftime('%Y-%m-%d')

def generate_donors_data(count=200):
    donors = []
    interest_areas = ['아동복지', '노인복지', '장애인복지', '다문화가정', '환경보호', '재난구호']
    payment_methods = ['신용카드', '계좌이체', '간편결제']
    
    # 정기후원 금액 후보
    regular_amounts = [5000, 10000, 20000, 30000, 50000, 100000]
    # 일시후원 금액 후보
    one_time_amounts = [10000, 30000, 50000, 100000, 200000, 500000]

    for i in range(1, count + 1):
        donor_id = f"D{i:04d}"
        name = generate_korean_name()
        phone = generate_phone()
        email = generate_email(name)
        birthday = generate_birthday()
        
        # 정기후원 80%, 일시후원 20%
        donation_type = random.choices(['정기후원', '일시후원'], weights=[80, 20], k=1)[0]
        
        if donation_type == '정기후원':
            donation_amount = random.choice(regular_amounts)
            status = random.choices(['활성', '중단'], weights=[90, 10], k=1)[0]
        else:
            donation_amount = random.choice(one_time_amounts)
            status = '완료'
            
        payment_method = random.choice(payment_methods)
        join_date = generate_join_date()
        interest_area = random.choice(interest_areas)
        
        donors.append({
            'donor_id': donor_id,
            'name': name,
            'phone': phone,
            'email': email,
            'birthday': birthday,
            'donation_type': donation_type,
            'donation_amount': donation_amount,
            'payment_method': payment_method,
            'join_date': join_date,
            'status': status,
            'interest_area': interest_area
        })
    return donors

def save_to_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_to_csv(data, filepath):
    if not data:
        return
    keys = data[0].keys()
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f: # utf-8-sig for Excel compatibility
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

def verify_data(json_path, csv_path, expected_count=200):
    print("=== 데이터 검증 시작 ===")
    
    # 1. 파일 존재 여부 확인
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON 파일이 없습니다: {json_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV 파일이 없습니다: {csv_path}")
    print("- JSON, CSV 파일 생성 확인: 완료")
    
    # 2. JSON 데이터 검증
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        
    if len(json_data) != expected_count:
        raise ValueError(f"JSON 데이터 개수가 일치하지 않습니다. 기대값: {expected_count}, 실제값: {len(json_data)}")
    print(f"- JSON 레코드 개수 검증 ({expected_count}개): 완료")
    
    # 3. CSV 데이터 검증
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_data = list(reader)
        
    if len(csv_data) != expected_count:
        raise ValueError(f"CSV 데이터 개수가 일치하지 않습니다. 기대값: {expected_count}, 실제값: {len(csv_data)}")
    print(f"- CSV 레코드 개수 검증 ({expected_count}개): 완료")

    # 4. 필드 구성 및 데이터 포맷 검증
    phone_pattern = re.compile(r'^010-\d{4}-\d{4}$')
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    required_keys = {
        'donor_id', 'name', 'phone', 'email', 'birthday', 
        'donation_type', 'donation_amount', 'payment_method', 
        'join_date', 'status', 'interest_area'
    }
    
    for idx, item in enumerate(json_data):
        # 키 존재 검사
        item_keys = set(item.keys())
        missing_keys = required_keys - item_keys
        if missing_keys:
            raise KeyError(f"Index {idx}: 필수 키 누락 {missing_keys}")
            
        # 값 타입 및 포맷 검사
        if not phone_pattern.match(item['phone']):
            raise ValueError(f"Index {idx}: 잘못된 전화번호 포맷 '{item['phone']}'")
            
        if not date_pattern.match(item['birthday']):
            raise ValueError(f"Index {idx}: 잘못된 생일 날짜 포맷 '{item['birthday']}'")
            
        if not date_pattern.match(item['join_date']):
            raise ValueError(f"Index {idx}: 잘못된 가입일 날짜 포맷 '{item['join_date']}'")
            
        if '@' not in item['email']:
            raise ValueError(f"Index {idx}: 잘못된 이메일 포맷 '{item['email']}'")
            
        if item['donation_type'] not in ['정기후원', '일시후원']:
            raise ValueError(f"Index {idx}: 잘못된 후원 유형 '{item['donation_type']}'")
            
        if not isinstance(item['donation_amount'], int) or item['donation_amount'] <= 0:
            raise ValueError(f"Index {idx}: 잘못된 후원 금액 '{item['donation_amount']}'")

    print("- 전체 데이터 필드 구성 및 포맷 무결성 검증: 완료")
    print("🎉 모든 데이터 검증이 정상적으로 통과되었습니다!")

if __name__ == "__main__":
    donors = generate_donors_data(1200)
    
    json_file = "donors.json"
    csv_file = "donors.csv"
    
    save_to_json(donors, json_file)
    save_to_csv(donors, csv_file)
    
    print(f"데이터 파일 생성 완료: {json_file}, {csv_file}")
    
    # 자체 검증 실행
    verify_data(json_file, csv_file, 1200)
