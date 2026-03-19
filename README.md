# 종금 웹 대시보드

엑셀 `DASHBOARD` 시트의 수식 로직을 FastAPI 기반 웹 대시보드로 옮긴 로컬 프로젝트입니다.  
원본 데이터는 `1. 수신잔고`, `2. 운용자산` 시트 또는 동일 구조의 CSV 파일을 사용합니다.

## 실행

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn dashboard_app.main:app --reload
```

브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000) 으로 접속합니다.

## 원본 반영 방식

1. 기본적으로 현재 폴더의 `대시보드 AI 기초자료 만들기_sample.xlsx`를 읽습니다.
2. 화면 상단에서 `.xlsx` 파일 1개를 업로드하면 최신 원본으로 자동 전환됩니다.
3. CSV로 운영할 경우 `수신잔고.csv`와 `운용자산.csv` 두 파일을 함께 업로드하면 됩니다.
4. 업로드 파일은 `data/input/` 아래 저장되고, 가장 최근 파일/묶음을 우선 사용합니다.

## 추가한 개선 사항

- 원본 엑셀의 `Duration` 수식 오류를 그대로 재현하면서도, raw `듀레이션` 컬럼 기준 보정값을 별도 노출
- 업로드 없이도 원본 시트 preview 확인 가능
- raw 시트에서 직접 나오지 않는 규제 보조 지표는 로컬 JSON으로 저장/수정 가능
- 데이터 row 수, 분류 누락 여부 등 간단한 데이터 품질 카드 제공

## 테스트

```bash
source .venv/bin/activate
pytest
```
