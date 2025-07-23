'use client';

import { useClerk, UserButton, SignedIn, SignedOut } from '@clerk/nextjs';
import { Button } from '@mui/material';

export default function AuthButtons() {
  const { openSignIn } = useClerk();

  return (
    <>
      <SignedIn>
        <UserButton afterSignOutUrl="/" />
      </SignedIn>
      <SignedOut>
        <Button variant="contained" onClick={() => openSignIn()}>
          Sign In
        </Button>
      </SignedOut>
    </>
  );
}