import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL;

export async function POST(request: NextRequest) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "BACKEND_URL not configured — cannot proxy upload" },
        { status: 503 }
      );
    }

    const formData = await request.formData();
    const file = formData.get("file");
    if (!file || !(file instanceof File)) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const backendForm = new FormData();
    backendForm.append("file", file);

    const clientId = formData.get("client_id") || "beurer";
    const backendRes = await fetch(
      `${BACKEND_URL}/api/v1/social-listening/import/service-cases?client_id=${clientId}`,
      { method: "POST", body: backendForm }
    );

    if (!backendRes.ok) {
      const err = await backendRes.text();
      return NextResponse.json(
        { error: `Backend error: ${err}` },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
