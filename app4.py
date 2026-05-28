import streamlit as st
import google.generativeai as genai
import json
from pypdf import PdfReader
import io

# ==========================================
# 1. Gemini API 인증 및 사이드바 설정
# ==========================================
st.set_page_config(page_title="QuoteCheck AI Pro (전권 학습형)", page_icon="📱", layout="wide")

st.sidebar.header("🎓 학습자 세션")
st.sidebar.info("**사용자:** 심호준 학생\n**소속:** 국방디지털융합학과\n**과목:** 대학 글쓰기 (03분반)")

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 AI 및 데이터 설정")
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.sidebar.warning("⚠️ 실시간 파일 분석을 위해 Gemini API Key가 필요합니다.")

# AI 프롬프트 가이드라인 정의
SYSTEM_INSTRUCTION = """
당신은 아주대학교 [대학 글쓰기] 과목의 인공지능 교육 튜터입니다.
제공된 책 전권 텍스트 데이터(Context)를 바탕으로, 학생이 입력한 '페이지 번호'와 '인용구'를 정밀 검증해야 합니다.

당신의 임무:
1. 제공된 책 데이터에서 학생이 말한 '페이지 번호'의 실제 원문을 찾아내십시오.
2. 학생이 적은 인용구와 진짜 원문을 비교하여 자구 일치도(%), 인용 유형을 판별하십시오.
3. 원문과 비교해 조사가 바뀌었거나 의미가 왜곡된 단어가 있다면 찾아내십시오.
4. 연구 윤리 및 미디어 리터러시 관점에서 학생에게 피드백을 주십시오.

반드시 다른 설명 없이 오직 아래 JSON 형태로만 응답하십시오.
{
  "found_origin_text": "당신이 책 데이터에서 찾아낸 해당 페이지의 실제 원문 문장",
  "score": 0~100 사이의 일치도 점수,
  "status": "안전", "주의", "위험" 중 하나 (90이상 안전, 60~89 주의, 60미만 위험),
  "quote_type": "직접 인용", "간접 인용(말바꾸기)", "출처 오류/왜곡" 중 하나,
  "mismatch_words": ["원문과 다르게 변형되거나 누락된 단어 리스트"],
  "feedback": "이 등급을 준 이유와 올바른 인용 규칙, 문맥 왜곡 방지를 위한 비판적 사고 조언이 담긴 친절한 줄글 피드백"
}
"""

# ==========================================
# 2. 파일 처리 함수 (PDF/TXT 가공)
# ==========================================
def extract_text_from_file(uploaded_file):
    """업로드된 파일에서 페이지별로 텍스트를 추출하여 시스템이 읽을 수 있게 정렬합니다."""
    book_pages_data = ""
    
    if uploaded_file.name.endswith('.pdf'):
        pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
        for i, page in enumerate(pdf_reader.pages):
            # 실제 책의 페이지와 맞추기 위해 [Page X] 태그를 붙여 텍스트화함
            text = page.extract_text()
            if text:
                book_pages_data += f"\n--- [Page {i+1}] ---\n{text}\n"
    elif uploaded_file.name.endswith('.txt'):
        # 일반 텍스트 파일의 경우
        book_pages_data = uploaded_file.read().decode("utf-8")
        
    return book_pages_data

# ==========================================
# 3. Gemini 실시간 도서 분석 엔진
# ==========================================
def analyze_quote_with_entire_book(book_text, page_num, user_quote):
    if not api_key:
        # API 키가 없을 때 시연을 위한 가상 리포트 데이터
        return {
            "found_origin_text": "(샘플 원문) 보통의 삶을 살다 보통의 나이에 죽는 것, 나는 언제나 그런 것이 기적이라 믿어왔다.",
            "score": 85, "status": "주의", "quote_type": "간접 인용(말바꾸기)",
            "mismatch_words": ["평범하게", "보통의"],
            "feedback": "[API 키 미입력 상태 - 가이드 모드] 문맥의 의미는 비슷하지만 저자의 고유한 시적 표현인 '보통의 삶'을 '평범한 삶'으로 임의 변경했습니다. 직접 인용 시 자구를 유지하거나, 간접 인용 시 출처 양식을 더 정확히 다듬어야 합니다."
        }

    # Gemini에게 전달할 질문 조립
    prompt = f"""
    [지정 도서 전권 데이터]:
    {book_text}

    [학생 요청 정보]:
    - 검증 대상 페이지 번호: {page_num}페이지
    - 학생이 과제에 쓴 인용 문장: "{user_quote}"

    위 도서 데이터에서 해당 페이지를 찾아 원문을 확인하고, 학생의 인용구 신뢰도를 판별하여 지정된 JSON 양식으로만 답변하세요.
    """

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",  # 컨텍스트 창이 크고 속도가 빠른 1.5 모델 사용
            generation_config={"response_mime_type": "application/json"},
            system_instruction=SYSTEM_INSTRUCTION
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Gemini API 실시간 분석 중 에러가 발생했습니다: {e}")
        return None

# ==========================================
# 4. 웹 어플리케이션 화면 설계 (UI)
# ==========================================
def main():
    st.title("📱 QuoteCheck AI v3.0 (도서 전권 학습형)")
    st.caption("Gemini LLM Long-Context Window 기술 탑재 — 아주대학교 [대학 글쓰기] 디지털 리터러시 플랫폼")
    st.markdown("---")
    
    left_col, right_col = st.columns([1.1, 0.9])
    
    with left_col:
        st.subheader("📚 1단계: 검증 도서 파일 등록 및 인용구 입력")
        
        # [기능 추가] 책 파일을 통째로 올리는 업로더 창
        uploaded_file = st.file_uploader(
            "검증할 도서의 전체 파일(PDF 또는 TXT)을 업로드하세요", 
            type=["pdf", "txt"],
            help="책 1쪽부터 마지막 쪽까지 포함된 스캔본이나 텍스트본을 올리면 AI가 통째로 학습합니다."
        )
        
        c1, c2 = st.columns([1, 2])
        with c1:
            page_num = st.text_input("📄 검증할 페이지 번호 입력", placeholder="예: 47")
        with c2:
            st.write("") # 간격 맞춤용
            st.caption("⚠️ 업로드한 파일의 실제 페이지 번호와 일치해야 정밀한 대조가 가능합니다.")
            
        user_quote = st.text_area(
            "✍️ 자신이 작성한 에세이 속 인용구 입력",
            placeholder="예시: 김애란은 소설 두근두근 내 인생에서 평범한 삶을 살다가 평범한 나이에 죽는 것이 곧 기적이라고 말했다.",
            height=120
        )
        
        if st.button("🚀 Gemini 실시간 전수 검증 시작"):
            if not uploaded_file:
                st.warning("도서 원문 파일(PDF/TXT)을 먼저 업로드해 주세요.")
            elif not page_num.strip():
                st.warning("확인할 페이지 번호를 입력해 주세요.")
            elif not user_quote.strip():
                st.warning("과제에 작성한 인용 문장을 입력해 주세요.")
            else:
                with st.spinner("Gemini AI가 업로드된 도서 전권을 분석하여 해당 페이지의 원문을 찾는 중입니다..."):
                    # 1. 파일에서 텍스트 추출
                    book_text = extract_text_from_file(uploaded_file)
                    
                    # 2. Gemini 대용량 분석 호출
                    res = analyze_quote_with_entire_book(book_text, page_num, user_quote)
                    
                    if res:
                        st.session_state['v3_res'] = res
                        
                        # 신호등 등급 시각화
                        score = res["score"]
                        status = res["status"]
                        
                        if status == "안전":
                            st.success(f"### 🟢 [{status}] 인용 신뢰도 점수: {score}%")
                        elif status == "주의":
                            st.warning(f"### 🟡 [{status}] 인용 신뢰도 점수: {score}%")
                        else:
                            st.error(f"### 🔴 [{status}] 인용 신뢰도 점수: {score}%")
                            
                        # AI가 책 전체에서 찾아낸 실제 원문 노출
                        st.info(f"📖 **Gemini가 책에서 찾아낸 진짜 원문 ({page_num}p):**\n\n\"{res['found_origin_text']}\"")
                        st.write(f"📊 **AI 판별 인용 유형:** `{res['quote_type']}`")
                        
                        if res["mismatch_words"]:
                            st.write("⚠️ **원문과 달라진 핵심 단어:**", ", ".join([f"`{w}`" for w in res["mismatch_words"]]))
                            
                        st.markdown("#### 📋 미디어 리터러시 튜터 피드백")
                        st.write(res["feedback"])

    with right_col:
        st.subheader("📝 2단계: 실시간 피드백 수정 연습장")
        st.write("왼쪽에서 AI가 찾아준 진짜 원문과 피드백 내용을 비교하며 올바른 문장으로 다시 고쳐 써보세요.")
        
        retry_text = st.text_area(
            "🔄 피드백 반영 수정안 작성 칸",
            placeholder="AI가 찾아낸 진짜 원문의 맥락에 맞게 표현을 고치거나 인용 형식을 수정해 보세요.",
            height=150
        )
        
        if st.button("✅ 수정본 자가진단 재검사"):
            if 'v3_res' not in st.session_state:
                st.info("먼저 왼쪽에서 책 파일을 올리고 1차 검사를 진행해 주세요.")
            elif not retry_text.strip():
                st.warning("수정한 문장을 입력해 주세요.")
            else:
                with st.spinner("수정본을 다시 전수 검사 중입니다..."):
                    book_text = extract_text_from_file(uploaded_file)
                    retry_res = analyze_quote_with_entire_book(book_text, page_num, retry_text)
                    
                    if retry_res["status"] == "안전":
                        st.balloons()
                        st.success("🎉 완벽합니다! AI가 책 본문과 대조한 결과, 정보의 무결성과 연구 윤리를 완벽하게 준수하여 수정되었음이 인증되었습니다!")
                    else:
                        st.warning(f"⚠️ 아직 보완할 요소가 있습니다. (현재 AI 점수: {retry_res['score']}%)\n\n원문을 다시 읽고 도전해 보세요!")

if __name__ == "__main__":
    main()
