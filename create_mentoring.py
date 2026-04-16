"""
삼성드림클래스 온라인 멘토링 자동 개설 스크립트
사용법: python3 create_mentoring.py
"""

import asyncio
from playwright.async_api import async_playwright

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
LOGIN_ID = "chaelin1098"
LOGIN_PW = "Cofls0727^^"
SITE_URL = "https://enabling.dreamclass.org/#/Login"

async def set_time(page, wrapper_index, hour, minute):
    """시간 피커 - JS로 Vue 컴포넌트 값 직접 설정"""
    await page.evaluate(f"""
        () => {{
            const wrappers = document.querySelectorAll('.hrd-time-picker-wrapper');
            const wrapper = wrappers[{wrapper_index}];
            if (!wrapper) return;

            // 시간 증가 버튼 클릭 방식
            const buttons = wrapper.querySelectorAll('button');
            // buttons[0]=시간증가, buttons[1]=시간감소, buttons[2]=분증가, buttons[3]=분감소
            for (let i = 0; i < {hour}; i++) {{
                if (buttons[0]) buttons[0].click();
            }}
            for (let i = 0; i < {minute}; i++) {{
                if (buttons[2]) buttons[2].click();
            }}
        }}
    """)
    await asyncio.sleep(0.3)


async def select_date(page, picker_index, day):
    """날짜 캘린더에서 날짜 선택 (JS 직접 클릭)"""
    # 해당 picker의 입력 클릭해서 캘린더 열기
    await page.evaluate(f"""
        () => {{
            const wrappers = document.querySelectorAll('.hrd-date-picker-wrapper');
            const wrapper = wrappers[{picker_index}];
            if (wrapper) {{
                const input = wrapper.querySelector('.date-picker-input');
                if (input) input.click();
            }}
        }}
    """)
    await asyncio.sleep(1.5)

    # 해당 picker 내부의 .date-picker-cover에서만 날짜 클릭
    found = await page.evaluate(f"""
        () => {{
            const wrappers = document.querySelectorAll('.hrd-date-picker-wrapper');
            const wrapper = wrappers[{picker_index}];
            if (!wrapper) return false;
            const cover = wrapper.querySelector('.date-picker-cover');
            if (!cover) return false;
            const btns = cover.querySelectorAll('button');
            for (const btn of btns) {{
                if (btn.textContent.trim() === '{day}') {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        }}
    """)
    await asyncio.sleep(0.8)
    if not found:
        print(f"  ⚠ 날짜 {day} 버튼을 못 찾음 (picker {picker_index})")


async def create_post(page, student, month, session, start_date_day, start_h, start_m, end_h, end_m):
    """
    글 1개 작성
    student: {"first_name": "서아", "nickname": "토리1004"}
    """
    first_name = student["first_name"]
    nickname   = student["nickname"]

    # ① 글쓰기 버튼
    await page.click("button:has-text('나의 생각과 느낌을 친구들과 공유해 보세요.')")
    await asyncio.sleep(1.5)

    # ② 제목
    await page.fill("input[placeholder='제목을 입력해 주세요.']", f"{first_name} 멘티 온라인 멘토링")

    # ③ 해시태그
    await page.fill("input[placeholder='키워드를 입력해 주세요. (엔터로 여러 키워드 등록 가능)']", "온라인멘토링")
    await page.keyboard.press("Enter")

    # ④ 본문 내용 (N월 N회차)
    await page.fill("textarea[placeholder='내용을 입력해 주세요.']", f"{month}월 {session}회차")

    # ⑤ LIVE 버튼 클릭
    await page.click("button.create.live", force=True)
    await asyncio.sleep(1.5)

    # ⑥ LIVE 모달 - 설명 입력
    await page.fill("textarea[placeholder='실시간 멘토링 설명을 입력해 주세요.']", "늦지 않게 만나요!")

    # ⑦ 시작 날짜 선택
    await select_date(page, 0, str(start_date_day))
    await asyncio.sleep(0.5)

    # ⑧ 시작 시간 설정
    await set_time(page, 0, start_h, start_m)
    await asyncio.sleep(0.5)

    # ⑨ 종료 날짜 선택
    await select_date(page, 1, str(start_date_day))
    await asyncio.sleep(0.5)

    # ⑩ 종료 시간 설정
    await set_time(page, 1, end_h, end_m)
    await asyncio.sleep(0.5)

    # ⑩-b 상태 확인 스크린샷
    await page.screenshot(path=f"/tmp/before_confirm.png")

    # ⑪ 확인 버튼 (live-pop 모달 내에서 클릭)
    await page.evaluate("""
        () => {
            // live-pop 모달 안의 확인 버튼 클릭
            const modal = document.querySelector('.live-pop');
            if (modal) {
                const btns = modal.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.trim() === '확인') {
                        btn.click();
                        return;
                    }
                }
            }
            // 폴백: 모든 visible 확인 버튼
            const allBtns = document.querySelectorAll('button');
            for (const btn of allBtns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === '확인' && rect.width > 0 && rect.height > 0) {
                    btn.click();
                    return;
                }
            }
        }
    """)
    await asyncio.sleep(1.5)

    # ⑫ 공개 설정 드롭다운 열기 (JS로)
    await page.evaluate("""
        () => {
            const slots = document.querySelectorAll('.v-select__slot');
            for (const slot of slots) {
                const rect = slot.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    slot.click();
                    return;
                }
            }
        }
    """)
    await asyncio.sleep(1)
    await page.screenshot(path=f"/tmp/dropdown_open.png")

    # 옵션 확인
    options = await page.evaluate("""
        () => Array.from(document.querySelectorAll('.v-list-item__title'))
            .filter(el => el.getBoundingClientRect().height > 0)
            .map(el => el.textContent.trim())
    """)
    print(f"  공개 옵션: {options}")

    # 사용자지정 선택
    await page.evaluate("""
        () => {
            const items = document.querySelectorAll('.v-list-item__title');
            for (const item of items) {
                const rect = item.getBoundingClientRect();
                if (rect.height > 0 && (item.textContent.includes('사용자') || item.textContent.includes('지정'))) {
                    item.click();
                    return;
                }
            }
        }
    """)
    await asyncio.sleep(1)

    await page.screenshot(path=f"/tmp/before_submit_{first_name}.png")
    print(f"  ✓ {first_name}({nickname}) 글 작성 완료 - 확인 후 등록하기 클릭 예정")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        page = await browser.new_page()
        page.set_default_timeout(60000)

        # 로그인
        await page.goto(SITE_URL, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        await page.fill("input[placeholder='아이디를 입력해 주세요.']", LOGIN_ID)
        await page.fill("input[placeholder='비밀번호를 입력해 주세요.']", LOGIN_PW)
        await page.press("input[placeholder='비밀번호를 입력해 주세요.']", "Enter")
        await asyncio.sleep(3)
        print("✓ 로그인")

        # 우리반 멘토링 이동
        await page.click("button.btn-category")
        await asyncio.sleep(1)
        await page.evaluate("document.querySelector('a.category__link').click()")
        await asyncio.sleep(2)
        print("✓ 우리반 멘토링")

        # 테스트: 서아(토리1004) 4/18 9:35 ~ 10:05
        student = {"first_name": "서아", "nickname": "토리1004"}
        await create_post(
            page,
            student=student,
            month=4, session=1,
            start_date_day=18,
            start_h=9,  start_m=35,
            end_h=10,   end_m=5,
        )

        print("\n브라우저 열어둠 - 공개 설정 확인 후 직접 등록하기 눌러주세요")
        await asyncio.sleep(600)
        await browser.close()

asyncio.run(main())
