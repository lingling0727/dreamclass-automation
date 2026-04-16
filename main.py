"""
삼성드림클래스 온라인 멘토링 자동 개설
사용법: python3 main.py

실행하면 schedule.csv 에 적힌 일정대로 자동 개설합니다.
"""

import asyncio
import json
import csv
from playwright.async_api import async_playwright

from config import LOGIN_ID, LOGIN_PW, SITE_URL, HEADLESS, SLOW_MO
from create_mentoring import create_post


# 1. 학생 정보 로드
def load_students():
    with open('students.json', 'r', encoding='utf-8') as f:
        student_list = json.load(f)
    # 이름으로 찾기 쉽게 딕셔너리로 변환 
    return {s['name']: s for s in student_list}


# 2. 스케줄 파일 로드
def load_schedule():
    schedules = []
    with open('schedule.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schedules.append({
                'name': row['이름'].strip(),
                'month': int(row['월']),
                'session': int(row['회차']),
                'day': int(row['일']),
                'start_h': int(row['시작시']),
                'start_m': int(row['시작분']),
            })
    return schedules


async def main():
    students_dict = load_students()
    schedules = load_schedule()

    print(f"📌 총 {len(schedules)}개의 멘토링 일정을 개설합니다!")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        page = await browser.new_page()
        page.set_default_timeout(60000)

        # ── 로그인 ────────────────────────────────────────
        await page.goto(SITE_URL, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.fill("input[placeholder='아이디를 입력해 주세요.']", LOGIN_ID)
        await page.fill("input[placeholder='비밀번호를 입력해 주세요.']", LOGIN_PW)
        await page.press("input[placeholder='비밀번호를 입력해 주세요.']", "Enter")
        await asyncio.sleep(3)
        print("✓ 로그인")

        # ── 우리반 멘토링 게시판 이동 ─────────────────────
        await page.click("button.btn-category")
        await asyncio.sleep(1)
        await page.evaluate("document.querySelector('a.category__link').click()")
        await asyncio.sleep(2)
        print("✓ 우리반 멘토링")

        # ── 반복문! 스케줄 순서대로 개설 시작 ───────────────
        for idx, sched in enumerate(schedules, 1):
            name = sched['name']
            print(f"\n[{idx}/{len(schedules)}] {name} 멘티 ( {sched['month']}월 {sched['session']}회차 ) 개설 시작...")
            
            if name not in students_dict:
                print(f"  ❌ 에러: 파라미터 '{name}'을(를) students.json에서 찾을 수 없습니다! 건너뜁니다.")
                continue
                
            curr_student = students_dict[name]
            # 이름의 첫 글자(성)를 제외한 나머지 문자열 1: 을 first_name으로 설정
            curr_student['first_name'] = name[1:]


            start_h = sched['start_h']
            start_m = sched['start_m']
            
            # --- 29분 뒤 자동 계산! ---
            end_m = start_m + 29
            end_h = start_h
            if end_m >= 60:
                end_m -= 60
                end_h += 1

            await create_post(
                page,
                student=curr_student,
                month=sched['month'],
                session=sched['session'],
                start_date_day=sched['day'],
                start_h=start_h, start_m=start_m,
                end_h=end_h,     end_m=end_m
            )
            # 하나 올리고 서버 부하/렉 방지용 잠깐 대기
            await asyncio.sleep(3)

        print("\n✅ 모든 멘토링 개설 작업 완료!")
        await asyncio.sleep(3)
        await browser.close()


asyncio.run(main())
