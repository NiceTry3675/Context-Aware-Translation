#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def send_announcement(message, environment='local'):
    """
    한글 공지를 안전하게 전송합니다.
    
    Args:
        message (str): 전송할 공지 메시지
        environment (str): 'local' 또는 'production'
    """
    
    # 환경별 설정
    if environment == 'local':
        url = "http://localhost:8000/api/v1/admin/announcements"
        secret_key = os.getenv("DEV_SECRET_KEY")
    else:  # production
        url = "https://catrans.up.railway.app/api/v1/admin/announcements"
        secret_key = os.getenv("PROD_SECRET_KEY")
    
    # 공지 데이터 준비
    data = {
        "message": message,
        "is_active": True
    }
    
    try:
        print(f"📤 공지 전송 중... ({environment})")
        print(f"메시지: {message}")
        print(f"URL: {url}")
        
        # JSON 데이터 준비 (UTF-8 보장)
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        
        # 요청 준비
        req = urllib.request.Request(url, data=json_data)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        req.add_header('x-admin-secret', secret_key)
        
        # 요청 전송
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
            
            print("\n✅ 공지 전송 성공!")
            print(f"ID: {result['id']}")
            print(f"메시지: {result['message']}")
            print(f"활성 상태: {result['is_active']}")
            print(f"생성 시간: {result['created_at']}")
            
            # 메시지 검증
            if result['message'] == message:
                print("\n🎉 한글이 완벽하게 전송되었습니다!")
                return True
            else:
                print("\n❌ 메시지가 변조되었습니다.")
                print(f"원본: {message}")
                print(f"응답: {result['message']}")
                return False
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ HTTP 오류 {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"❌ 전송 오류: {e}")
        return False

def deactivate_announcement(announcement_id, environment='local'):
    """
    특정 공지를 비활성화합니다.
    """
    
    # 환경별 설정
    if environment == 'local':
        url = f"http://localhost:8000/api/v1/admin/announcements/{announcement_id}/deactivate"
        secret_key = os.getenv("DEV_SECRET_KEY")
    else:  # production
        url = f"https://catrans.up.railway.app/api/v1/admin/announcements/{announcement_id}/deactivate"
        secret_key = os.getenv("PROD_SECRET_KEY")
    
    try:
        print(f"🔇 공지 비활성화 중... (ID: {announcement_id})")
        
        # 요청 준비
        req = urllib.request.Request(url, method='PUT')
        req.add_header('x-admin-secret', secret_key)
        
        # 요청 전송
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
            
            print("\n✅ 공지 비활성화 성공!")
            print(f"ID: {result['id']}")
            print(f"메시지: {result['message']}")
            print(f"활성 상태: {result['is_active']}")
            
            return True
            
    except Exception as e:
        print(f"❌ 비활성화 오류: {e}")
        return False

def deactivate_all_announcements(environment='local'):
    """
    모든 활성 공지를 비활성화합니다.
    """
    
    # 환경별 설정
    if environment == 'local':
        url = "http://localhost:8000/api/v1/admin/announcements/deactivate-all"
        secret_key = os.getenv("DEV_SECRET_KEY")
    else:  # production
        url = "https://catrans.up.railway.app/api/v1/admin/announcements/deactivate-all"
        secret_key = os.getenv("PROD_SECRET_KEY")
    
    try:
        print("🔇 모든 공지 비활성화 중...")
        
        # 요청 준비
        req = urllib.request.Request(url, method='PUT')
        req.add_header('x-admin-secret', secret_key)
        
        # 요청 전송
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
            
            print("\n✅ 모든 공지 비활성화 성공!")
            print(f"메시지: {result['message']}")
            print(f"비활성화된 공지 수: {result['deactivated_count']}개")
            
            return True
            
    except Exception as e:
        print(f"❌ 비활성화 오류: {e}")
        return False

def main():
    """
    메인 함수 - 사용자 입력을 받아 공지를 전송합니다.
    """
    print("🚀 한글 공지 전송 도구")
    print("=" * 50)
    
    # 환경 선택
    print("환경을 선택하세요:")
    print("1. 로컬 개발환경 (localhost:8000)")
    print("2. 프로덕션 환경 (catrans.up.railway.app)")
    
    try:
        env_choice = input("선택 (1 또는 2): ").strip()
        environment = 'local' if env_choice == '1' else 'production'
        
        print(f"\n선택된 환경: {environment}")
        
        # 작업 선택
        print("\n작업을 선택하세요:")
        print("1. 새 공지 전송")
        print("2. 특정 공지 비활성화")
        print("3. 모든 공지 비활성화")
        
        action_choice = input("선택 (1, 2, 또는 3): ").strip()
        
        if action_choice == '1':
            # 새 공지 전송
            message = input("\n전송할 공지 메시지를 입력하세요: ").strip()
            if message:
                send_announcement(message, environment)
            else:
                print("❌ 메시지가 비어있습니다.")
                
        elif action_choice == '2':
            # 특정 공지 비활성화
            announcement_id = input("\n비활성화할 공지 ID를 입력하세요: ").strip()
            if announcement_id.isdigit():
                deactivate_announcement(int(announcement_id), environment)
            else:
                print("❌ 올바른 ID를 입력해주세요.")
                
        elif action_choice == '3':
            # 모든 공지 비활성화
            confirm = input("\n⚠️ 모든 활성 공지를 비활성화하시겠습니까? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                deactivate_all_announcements(environment)
            else:
                print("❌ 취소되었습니다.")
        else:
            print("❌ 올바른 선택이 아닙니다.")
            
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

# 사전 정의된 메시지들
PREDEFINED_MESSAGES = {
    "1": "📢 시스템 점검 안내: 오늘 밤 12시부터 2시간 동안 서비스가 일시 중단됩니다.",
    "2": "🎉 새로운 번역 모델이 추가되었습니다! Gemini 2.5 Flash를 체험해보세요.",
    "3": "⚠️ 긴급: 서버 부하로 인해 일시적으로 번역 속도가 느려질 수 있습니다.",
    "4": "✅ 시스템 점검 완료: 모든 서비스가 정상적으로 복구되었습니다.",
    "5": "🚀 서비스 업데이트: 번역 품질이 대폭 개선되었습니다!",
}

def quick_send():
    """
    빠른 전송 - 사전 정의된 메시지 사용
    """
    print("🚀 빠른 공지 전송")
    print("=" * 50)
    
    print("사전 정의된 메시지:")
    for key, message in PREDEFINED_MESSAGES.items():
        print(f"{key}. {message}")
    
    try:
        choice = input("\n메시지 번호를 선택하세요 (1-5): ").strip()
        if choice in PREDEFINED_MESSAGES:
            message = PREDEFINED_MESSAGES[choice]
            print(f"\n선택된 메시지: {message}")
            
            env_choice = input("환경 (1=로컬, 2=프로덕션): ").strip()
            environment = 'local' if env_choice == '1' else 'production'
            
            send_announcement(message, environment)
        else:
            print("❌ 올바른 번호를 선택해주세요.")
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_send()
    else:
        main() 