# 실시간 공지 전송 매뉴얼

이 문서는 관리자가 모든 사용자에게 실시간으로 공지를 보내는 방법을 설명합니다.

**요구사항:**
- PowerShell 터미널 사용
- 올바른 백엔드 URL과 관리자 시크릿 키

---

### 1. 새로운 공지 생성 및 전송

아래 PowerShell 명령어를 사용하여 새로운 공지를 생성하고 모든 클라이언트에 즉시 전송합니다. 이 명령어를 실행하면 이전 공지는 자동으로 비활성화되고 새로운 공지가 활성화됩니다.

**명령어:**
```powershell
Invoke-RestMethod -Uri "https://catrans.up.railway.app/api/v1/admin/announcements" -Method Post -Headers @{"X-Admin-Secret"="catrans"} -ContentType 'application/json; charset=utf-8' -Body '{"message": "클라우드 서비스 전체 공지입니다.", "is_active": true}'
```

**설명:**
- **-Uri**: 백엔드의 공지 생성 엔드포인트 주소입니다.
- **-Headers**: 관리자 인증을 위한 시크릿 키(`X-Admin-Secret`)를 포함합니다.
- **-Body**: 전송할 공지 메시지(`message`)를 JSON 형식으로 지정합니다.

---

### 2. 현재 공지 비활성화

현재 활성화된 공지를 화면에서 내리고 싶을 때 사용합니다. 비활성화할 공지의 `id`가 필요합니다. (id는 생성 명령어 실행 시 반환 값에서 확인할 수 있습니다.)

**명령어 예시 (id가 1인 공지를 비활성화):**
```powershell
Invoke-RestMethod -Uri "https://catrans.up.railway.app/api/v1/admin/announcements/1/deactivate" -Method Put -Headers @{"X-Admin-Secret"="catrans"}
```

**설명:**
- **-Uri**: 비활성화할 공지의 `id`를 URL에 포함하여 지정합니다.
- **-Method**: `Put` 요청을 사용합니다.
