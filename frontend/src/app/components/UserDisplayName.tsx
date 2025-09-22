'use client';

import { useUser } from '@clerk/nextjs';
import type { components } from '@/types/api';

// Support both legacy and new API schema types
interface LegacyAuthor {
  id: number;
  clerk_user_id: string;
  name?: string | null;
  email?: string | null;
  role: string;
}

// AuthorSummary from backend (new schema)
type AuthorSummary = components['schemas']['AuthorSummary'];

type Author = LegacyAuthor | AuthorSummary;

interface UserDisplayNameProps {
  author: Author;
  showRole?: boolean;
  variant?: 'full' | 'short';
}

// Type guard to check if author is legacy type
function isLegacyAuthor(author: Author): author is LegacyAuthor {
  return 'clerk_user_id' in author;
}

export default function UserDisplayName({
  author,
  showRole = false,
  variant = 'full'
}: UserDisplayNameProps) {
  const { user } = useUser();

  // Determine if this author is the currently signed-in user
  const isCurrentUser = (() => {
    if (!user) return false;
    // Legacy: compare Clerk IDs
    if (isLegacyAuthor(author)) return user.id === author.clerk_user_id;
    // New schema: compare numeric id if available via publicMetadata (optional)
    // We can't reliably map Clerk user to numeric DB id on the client, so only rely on name display below.
    return false;
  })();

  // Decide display name with sensible fallbacks
  const getDisplayName = () => {
    // Prefer Clerk username for the current user for better UX
    if (isCurrentUser && user) {
      if (user.username) return user.username;
      const full = `${user.firstName || ''} ${user.lastName || ''}`.trim();
      if (full) return full;
    }

    // Use provided author name if present
    const providedName = (author as any).name as string | undefined;
    if (providedName && providedName.trim()) return providedName.trim();

    // Legacy fallback: derive from email
    if (isLegacyAuthor(author) && author.email) {
      const emailUser = author.email.split('@')[0];
      return variant === 'short'
        ? (emailUser.length > 8 ? emailUser.substring(0, 8) + '...' : emailUser)
        : emailUser;
    }

    // Generic fallback
    return isCurrentUser ? '나' : '사용자';
  };

  const displayName = getDisplayName();
  const isAdmin = isLegacyAuthor(author) && author.role === 'admin';

  return (
    <span>
      {displayName}
      {isCurrentUser && variant === 'full' && !displayName.includes('나') && ' (나)'}
      {showRole && isAdmin && ' 👑'}
    </span>
  );
} 