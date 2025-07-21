'use client';

import { useUser } from '@clerk/nextjs';

interface Author {
  id: number;
  clerk_user_id: string;
  name: string | null;
  email: string | null;
  role: string;
}

interface UserDisplayNameProps {
  author: Author;
  showRole?: boolean;
  variant?: 'full' | 'short';
}

export default function UserDisplayName({ 
  author, 
  showRole = false, 
  variant = 'full' 
}: UserDisplayNameProps) {
  const { user } = useUser();
  
  // 현재 사용자인지 확인
  const isCurrentUser = user?.id === author.clerk_user_id;
  
  // 표시할 이름 결정 로직 (사용자명 우선)
  const getDisplayName = () => {
    // 1. 현재 사용자인 경우 Clerk에서 사용자명 우선 가져오기
    if (isCurrentUser && user) {
      if (user.username) {
        return user.username;
      }
      if (user.firstName || user.lastName) {
        return `${user.firstName || ''} ${user.lastName || ''}`.trim();
      }
    }
    
    // 2. 데이터베이스의 name 필드 사용 (보통 username이 저장됨)
    if (author.name && author.name.trim()) {
      return author.name.trim();
    }
    
    // 3. 이메일에서 사용자명 추출
    if (author.email) {
      const emailUser = author.email.split('@')[0];
      return variant === 'short' ? 
        (emailUser.length > 8 ? emailUser.substring(0, 8) + '...' : emailUser) : 
        emailUser;
    }
    
    // 4. 기본값
    return isCurrentUser ? '나' : '사용자';
  };
  
  const displayName = getDisplayName();
  const isAdmin = author.role === 'admin';
  
  return (
    <span>
      {displayName}
      {isCurrentUser && variant === 'full' && !displayName.includes('나') && ' (나)'}
      {showRole && isAdmin && ' 👑'}
    </span>
  );
} 