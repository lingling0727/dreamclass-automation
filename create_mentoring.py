"""
삼성드림클래스 온라인 멘토링 자동 개설 - 핵심 로직 모음
(실행은 main.py에서)
"""

import asyncio


async def set_time(page, wrapper_index, hour, minute):
    """시간 피커 - JS로 Vue 컴포넌트 값 직접 설정"""
    await page.evaluate(f"""
        () => {{
            const wrappers = document.querySelectorAll('.hrd-time-picker-wrapper');
            const wrapper = wrappers[{wrapper_index}];
            if (!wrapper) return;

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
    """날짜 캘린더에서 날짜 선택 - Playwright 실제 클릭으로 Vue 이벤트 트리거"""
    # Playwright 실제 클릭 (JS .click()은 Vue 이벤트를 트리거 못할 수 있음)
    try:
        # .date-picker-input 이 wrapper 안에 2개 있어서 .first 로 첫 번째 선택
        date_input = page.locator('.hrd-date-picker-wrapper').nth(picker_index).locator('.date-picker-input').first
        await date_input.click(force=True)
    except Exception as e:
        print(f"  [날짜] date-picker-input 클릭 실패, wrapper 클릭 시도: {e}")
        try:
            await page.locator('.hrd-date-picker-wrapper').nth(picker_index).click(force=True)
        except Exception as e2:
            print(f"  [날짜] wrapper 클릭도 실패: {e2}")

    await asyncio.sleep(1.5)

    # 전체 페이지 버튼 탐색 (Vue portal 패턴: 달력이 wrapper 밖에 렌더링됨)
    all_buttons = await page.query_selector_all('button')
    clicked = False
    for btn in all_buttons:
        try:
            text = await btn.inner_text()
            visible = await btn.is_visible()
            if text.strip() == str(day) and visible:
                await btn.click()
                clicked = True
                break
        except:
            continue

    await asyncio.sleep(0.8)
    if not clicked:
        print(f"  ⚠ 날짜 {day} 버튼을 못 찾음 (picker {picker_index})")


async def select_user(page, nickname):
    """사용자 선택 모달 - 닉네임 검색 후 + 클릭 → 선택"""
    # 모달 뜰 때까지 대기
    await page.wait_for_selector("text=사용자 선택", timeout=10000)
    await asyncio.sleep(1)

    # 닉네임으로 검색
    await page.fill("input[placeholder='멤버를 검색하세요.']", nickname)
    await asyncio.sleep(1.5)

    # + 버튼 클릭: 취소/선택/확인 제외하고 작은 버튼 찾기
    all_buttons = await page.query_selector_all('button')
    clicked = False
    for btn in all_buttons:
        try:
            visible = await btn.is_visible()
            if not visible:
                continue
            text = (await btn.inner_text()).strip()
            if text in ('취소', '선택', '확인'):
                continue
            # '추가' = 추가하기(+) 버튼, '+' 텍스트, 또는 작은 아이콘 버튼
            if text in ('+', '추가'):
                await btn.click()
                clicked = True
                break
            if text == '':
                box = await btn.bounding_box()
                html = await btn.inner_html()
                if box and box['width'] < 60 and (
                    'plus' in html.lower() or '+' in html or 'add' in html.lower()
                ):
                    await btn.click()
                    clicked = True
                    break
        except:
            continue

    await asyncio.sleep(1.5)  # 추가 후 애니메이션 대기

    if not clicked:
        print(f"  ⚠ '{nickname}' + 버튼 못 찾음")
        return False

    # 선택 버튼 클릭 — JS로 정확히 80px짜리 '선택' 버튼만 타겟
    confirmed = await page.evaluate("""
        () => {
            const btns = Array.from(document.querySelectorAll('button'));
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                const text = btn.textContent.trim();
                if (text === '선택' && rect.width > 60 && rect.width < 120 && rect.height > 0) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }
    """)
    if not confirmed:
        await page.click("text=선택")  # 폴백
    await asyncio.sleep(1)
    print(f"  ✓ 사용자 선택 완료: {nickname}")
    return True



async def create_post(page, student, month, session, start_date_day, start_h, start_m, end_h, end_m):
    """
    멘토링 게시글 1개 작성 및 등록
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

    # ⑪ LIVE 모달 확인 버튼
    await page.evaluate("""
        () => {
            const modal = document.querySelector('.live-pop');
            if (modal) {
                const btns = modal.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.trim() === '확인') { btn.click(); return; }
                }
            }
            const allBtns = document.querySelectorAll('button');
            for (const btn of allBtns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === '확인' && rect.width > 0 && rect.height > 0) {
                    btn.click(); return;
                }
            }
        }
    """)
    await asyncio.sleep(1.5)

    # ⑫ 공개 설정 드롭다운 열기 (.v-input__slot 클릭 - Vuetify 표준)
    try:
        await page.locator('.v-input__slot').click()
    except:
        elements = page.locator("text=우리반공개")
        count = await elements.count()
        for i in range(count):
            el = elements.nth(i)
            try:
                if await el.is_visible():
                    await el.click()
                    break
            except:
                continue
    await asyncio.sleep(1)

    # ⑬ '사용자 지정 공개' 선택
    await page.click("text=사용자 지정 공개")
    await asyncio.sleep(1)
    print("  ✓ 공개 설정: 사용자 지정 공개")

    # ⑭ 사용자 선택 모달 자동 처리
    await select_user(page, nickname)
    await asyncio.sleep(1)

    # ⑮ 등록하기 클릭
    await page.click("button:has-text('등록하기')")
    await asyncio.sleep(2)

    # ⑯ 최종 등록 확인 팝업 (예: "등록하시겠습니까?" 모달의 '확인' 버튼)
    try:
        # 팝업 대기
        await asyncio.sleep(1)
        
        # JS로 사이즈가 명확하고 화면에 보이는 '확인' 버튼만 타겟팅 (보통 맨 마지막에 위치함)
        confirmed = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                // 뒤에서부터 탐색 (가장 최근에 뜬 모달이 DOM 끝 쪽에 있을 확률이 높음)
                for (let i = btns.length - 1; i >= 0; i--) {
                    const btn = btns[i];
                    const rect = btn.getBoundingClientRect();
                    const text = btn.textContent.trim();
                    if (text === '확인' && rect.width > 60 && rect.width < 100 && rect.height > 0) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        
        if confirmed:
            print("  ✓ 최종 등록 확인(모달) 완료")
        else:
            # 폴백용 클릭 시도
            await page.locator("button:has-text('확인')").last.click(timeout=3000)
            print("  ✓ 최종 등록 확인(모달 폴백) 완료")
            
        await asyncio.sleep(1.5)
    except Exception as e:
        print(f"  [참고] 추가 확인 팝업을 찾지 못했거나 이미 등록되었습니다. ({e})")

    print(f"  ✅ {first_name}({nickname}) 등록 완료!")
