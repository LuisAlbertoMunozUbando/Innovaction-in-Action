import { NextRequest, NextResponse } from 'next/server';

const API_URL = (process.env.SPARK_INNOVACTION_API_URL || '').replace(/\/$/, '');
const API_KEY = process.env.SPARK_INNOVACTION_API_KEY || '';

export async function POST(req: NextRequest) {
  if (!API_URL) {
    return NextResponse.json(
      { error: 'SPARK_INNOVACTION_API_URL is not configured on Vercel.' },
      { status: 500 }
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON request.' }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${API_URL}/generate`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...(API_KEY ? { 'x-api-key': API_KEY } : {}),
      },
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(115000),
    });

    const text = await upstream.text();

    if (!upstream.ok) {
      return NextResponse.json(
        {
          error: 'Innovaction Spark backend returned an error.',
          upstreamStatus: upstream.status,
          detail: text.slice(0, 2000),
        },
        { status: 502 }
      );
    }

    try {
      return NextResponse.json(JSON.parse(text));
    } catch {
      return NextResponse.json(
        {
          error: 'Innovaction Spark backend returned invalid JSON.',
          detail: text.slice(0, 2000),
        },
        { status: 502 }
      );
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: 'Could not reach Innovaction Spark backend.', detail: message },
      { status: 502 }
    );
  }
}
