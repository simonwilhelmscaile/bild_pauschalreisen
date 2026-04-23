import { NextRequest, NextResponse } from "next/server";

const LOGIN_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Beurer Dashboard — Login</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23C60050' width='100' height='100' rx='20'/%3E%3Ctext x='50' y='70' font-size='60' text-anchor='middle' fill='white' font-family='Inter,sans-serif' font-weight='700'%3EB%3C/text%3E%3C/svg%3E">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Inter, -apple-system, sans-serif;
      background: #f5f5f7;
    }
    .card {
      background: white;
      border-radius: 16px;
      padding: 48px 40px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      width: 100%;
      max-width: 380px;
    }
    .logo {
      width: 48px; height: 48px;
      background: linear-gradient(135deg, #C60050, #9E0040);
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      color: white; font-weight: 700; font-size: 24px;
      margin-bottom: 24px;
    }
    h1 { font-size: 20px; color: #1d1d1f; margin-bottom: 4px; }
    .subtitle { font-size: 14px; color: #86868b; margin-bottom: 32px; }
    input[type="password"] {
      width: 100%; padding: 12px 16px;
      border: 1.5px solid #e8e8ed; border-radius: 10px;
      font-size: 15px; outline: none;
      transition: border-color 0.2s;
    }
    input[type="password"]:focus { border-color: #C60050; }
    button {
      width: 100%; padding: 12px;
      background: linear-gradient(135deg, #C60050, #9E0040);
      color: white; border: none; border-radius: 10px;
      font-size: 15px; font-weight: 600; cursor: pointer;
      margin-top: 16px; transition: opacity 0.2s;
    }
    button:hover { opacity: 0.9; }
    .error {
      color: #ff3b30; font-size: 13px;
      margin-top: 12px; display: none; text-align: center;
    }
    .error.show { display: block; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">B</div>
    <h1>Social Listening Dashboard</h1>
    <p class="subtitle">Enter password to continue</p>
    <form method="POST" action="/api/auth">
      <input type="password" name="password" placeholder="Password" autofocus required />
      <button type="submit">Sign in</button>
      <p class="error __ERROR_CLASS__">Incorrect password</p>
    </form>
  </div>
</body>
</html>`;

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow auth and admin endpoints through (admin handles its own auth)
  if (pathname === "/api/auth" || pathname.startsWith("/api/admin")) {
    return NextResponse.next();
  }

  // Check for auth cookie
  const token = request.cookies.get("dashboard_token")?.value;
  const expectedToken = process.env.DASHBOARD_PASSWORD;

  // If no password is configured, allow all access
  if (!expectedToken) {
    return NextResponse.next();
  }

  if (token === expectedToken) {
    return NextResponse.next();
  }

  // Show login page
  const showError = request.nextUrl.searchParams.get("error") === "1";
  const html = LOGIN_HTML.replace(
    "__ERROR_CLASS__",
    showError ? "show" : ""
  );

  return new NextResponse(html, {
    status: 401,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
