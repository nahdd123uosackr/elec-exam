#!/usr/bin/env python3
"""
kinz.kr 브라우저 자동화로 정답 추출
- 각 시험의 모든 문제에 대해 "해설" 버튼 클릭
- reCAPTCHA 자동 처리됨 (headless Chromium)
- 정답 번호 + 정답률 + 해설 텍스트 추출
"""
import json, time, subprocess, sys

EXAMS = {
    6847: '2005-01',
    6846: '2005-02',
    6845: '2005-03',
    6844: '2006-01',
    6843: '2006-02',
    6842: '2006-03',
    6841: '2007-01',
    6840: '2007-02',
    6839: '2007-03',
    6838: '2008-01',
    6837: '2008-02',
    6836: '2008-03',
    6835: '2009-01',
    6834: '2009-02',
    6833: '2009-03',
}

# JavaScript: 모든 "해설" 버튼을 2초 간격으로 클릭
CLICK_ALL_JS = """
(function() {
    const buttons = document.querySelectorAll('.show-answer');
    const total = buttons.length;
    let clicked = 0;
    const interval = setInterval(() => {
        if (clicked >= total) {
            clearInterval(interval);
            window.__done = true;
            return;
        }
        buttons[clicked].click();
        clicked++;
    }, 2000);
    return total;
})();
"""

# JavaScript: 모든 정답 읽기
READ_ANSWERS_JS = """
(function() {
    const results = [];
    for (let i = 0; i < 100; i++) {
        const numEl = document.querySelector('#correctAnswer' + i + ' .correct-answer-number');
        const pctEl = document.querySelector('#correctAnswer' + i + ' .correct-percent');
        const textEl = document.querySelector('#correctAnswer' + i + ' .correct-answer-text');
        if (numEl) {
            const num = parseInt(numEl.textContent.replace(/[^0-9]/g, ''));
            const pct = pctEl ? pctEl.textContent.trim() : '';
            const text = textEl ? textEl.textContent.trim() : '';
            results.push({num, pct, text});
        }
    }
    return JSON.stringify(results);
})();
"""

if __name__ == '__main__':
    # 이건 브라우저 도구를 사용하는 메인 스크립트에서 호출됨
    # 여기서는 JS 템플릿만 제공
    print("Use browser tools to run this extraction")
    print("1. browser_navigate to https://www.kinz.kr/exam/<id>")
    print("2. browser_console: CLICK_ALL_JS")
    print("3. Wait ~200s for all clicks")
    print("4. browser_console: READ_ANSWERS_JS")
