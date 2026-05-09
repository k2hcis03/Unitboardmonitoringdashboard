# 개발 명령어

## 프론트엔드 (React/Vite, 포트 3000)
```powershell
npm install           # 의존성 설치
npm run dev           # 개발 서버 시작
npm run build         # 프로덕션 빌드
# 외부 접속 허용 (라즈베리파이에서)
npm run dev -- --host --open=false
```

## 백엔드 (Python/Litestar, 포트 9001)
```powershell
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py               # 서버 시작
```

## Sensor Viewer
```powershell
cd sensor_view
pip install -r requirements.txt
python app.py
```

## API 테스트
```powershell
curl http://localhost:9001/api/units/0
curl -X POST http://localhost:9001/api/gpio/control -H "Content-Type: application/json" -d '{\"unit_id\": 0, \"gpio_index\": 0, \"state\": true}'
```

## Git (Windows PowerShell)
```powershell
git status
git add <파일명>
git commit -m "커밋 메시지"
git log --oneline -10
```

## 유용한 Windows 명령어
```powershell
Get-ChildItem            # ls 대신
Select-String            # grep 대신
Get-Content              # cat 대신
```
