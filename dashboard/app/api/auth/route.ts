import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const password = formData.get("password") as string;
  const expected = process.env.DASHBOARD_PASSWORD;

  if (!expected || password !== expected) {
    // Redirect back to login with error
    const url = new URL("/", request.url);
    url.searchParams.set("error", "1");
    return NextResponse.redirect(url, 303);
  }

  // Set auth cookie and redirect to dashboard
  const response = NextResponse.redirect(new URL("/api/dashboard", request.url), 303);
  response.cookies.set("dashboard_token", password, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 90, // 90 days
    path: "/",
  });

  return response;
}
