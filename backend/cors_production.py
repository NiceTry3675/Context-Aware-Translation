# 프로덕션 배포 시 사용할 CORS 설정
# main.py에서 이 설정으로 교체해주세요

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 로컬 개발
        "https://your-frontend-domain.vercel.app",  # 실제 프론트엔드 도메인
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "accept",
        "accept-encoding", 
        "authorization",
        "content-type",
        "origin",
        "user-agent",
    ],
) 