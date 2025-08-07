import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isPublicRoute = createRouteMatcher([
  '/about(.*)', // Make the new about page public
  '/sign-in(.*)',
  '/sign-up(.*)',
]);

export default clerkMiddleware(async (auth, req) => {
  const { userId, orgId } = await auth();

  // If the user is not logged in and trying to access the root, redirect to about page
  if (!userId && req.nextUrl.pathname === '/') {
    const aboutUrl = new URL('/about', req.url);
    return Response.redirect(aboutUrl);
  }

  // Protect all other routes
  if (!isPublicRoute(req)) {
    auth.protect();
  }
});

export const config = {
  matcher: ['/((?!.*\..*|_next).*)', '/', '/(api|trpc)(.*)'],
};