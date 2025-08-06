import { SignIn } from "@clerk/nextjs";

export default function Page() {
  return (
    <SignIn 
      fallbackRedirectUrl="/canvas"
      signUpUrl="/sign-up"
    />
  );
}