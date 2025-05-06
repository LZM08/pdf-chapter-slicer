import fitz
import os
import requests
import traceback

api_key = ""
pdf_path = ""
output_folder = ""

if not api_key:
    api_key = input("🔑 Claude API Key를 입력하세요: ").strip()

if not pdf_path or not os.path.exists(pdf_path):
    pdf_path = input("📄 PDF 파일 경로를 입력하세요: ").strip()
    if not os.path.exists(pdf_path):
        print("❌ 유효한 PDF 경로가 아닙니다.")
        exit()

if not output_folder:
    output_folder = input("📂 분리된 PDF를 저장할 폴더명을 입력하세요: ").strip()

os.makedirs(output_folder, exist_ok=True)


def extract_toc_text(pdf_path):
    """PDF에서 목차(TOC)를 추출하여 텍스트로 반환"""
    doc = fitz.open(pdf_path)
    toc = doc.get_toc(simple=True)
    text_lines = []
    for item in toc:
        level, title, page = item
        indent = "  " * (level - 1)
        text_lines.append(f"{indent}- {title} (Page {page})")
    return "\n".join(text_lines)


def get_chapter_ranges_from_claude(toc_text, api_key):
    """Claude API를 사용하여 목차 텍스트에서 챕터 범위를 추출"""
    system_prompt = (
        "You will be given a Table of Contents from a book. "
        "Return only a JSON object that maps chapter titles to [start_page, end_page]. "
        "Infer ranges logically using indentation and page numbers. "
        "Do not explain anything. Only return JSON like: "
        '{ "Chapter 1: Intro": [1, 20], "Chapter 2: Basics": [21, 40] }'
    )

    headers = {
        "anthropic-version": "2023-06-01",
        "x-api-key": api_key,
        "content-type": "application/json"
    }

    payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1000,
        "temperature": 0,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": toc_text}
        ]
    }

    try:
        print("🔄 Claude API 요청 중...")
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        
        print(f"🔍 상태 코드: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ 응답 내용: {response.text}")
            return None
            
        response_data = response.json()
        content = response_data["content"][0]["text"]
        print("🧠 Claude 응답 결과:\n", content)
        
        chapter_ranges = eval(content)
        return chapter_ranges
            
    except Exception as e:
        print(f"⚠️ API 처리 중 오류: {e}")
        print(traceback.format_exc())
        return None


def manual_chapter_input():
    """수동으로 챕터 범위 입력 받기"""
    chapter_ranges = {}
    print("✏️ 수동으로 챕터 범위 입력을 시작합니다. (끝내려면 Enter)")
    while True:
        title = input("챕터 제목: ").strip()
        if not title:
            break
        start = input("  시작 페이지: ").strip()
        end = input("  끝 페이지: ").strip()
        if start.isdigit() and end.isdigit():
            chapter_ranges[title] = [int(start), int(end)]
    return chapter_ranges


def save_chapter_pdfs(pdf_path, chapter_ranges, output_folder):
    """PDF를 챕터별로 분할하여 저장"""
    doc = fitz.open(pdf_path)
    for title, (start, end) in chapter_ranges.items():
        new_doc = fitz.open()
        for i in range(start - 1, end):
            if 0 <= i < len(doc):
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
        if len(new_doc) == 0:
            print(f"⚠️ {title} 저장 안됨 (범위: {start}-{end})")
            continue
        clean_title = "".join(c if c.isalnum() or c.isspace() else "_" for c in title)
        output_path = os.path.join(output_folder, f"{clean_title}.pdf")
        new_doc.save(output_path)
        print(f"📄 저장됨: {output_path}")


def main():
    """메인 실행 함수"""
    try:
        print("📘 TOC 추출 중...")
        toc_text = extract_toc_text(pdf_path)
        
        chapter_ranges = get_chapter_ranges_from_claude(toc_text, api_key)

        if not chapter_ranges:
            print("📝 Claude 실패 → 수동 입력으로 전환")
            chapter_ranges = manual_chapter_input()

        if chapter_ranges:
            print("📌 사용될 챕터 범위:")
            for k, v in chapter_ranges.items():
                print(f"  {k}: {v}")
            save_chapter_pdfs(pdf_path, chapter_ranges, output_folder)
            print("✅ 챕터별 PDF 저장 완료")
        else:
            print("❌ 유효한 챕터 범위가 없습니다.")
    except Exception as e:
        print(f"⚠️ 프로그램 실행 중 오류 발생: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
