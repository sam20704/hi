// src/lib/apiClient.ts

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

export type HealthResponse = {
  status: string;
};

export type NLQueryResponse = {
  sql: string;
  columns: string[];
  rows: any[][];
  answer: string;
};

// --------------------
// Health Check
// --------------------
export async function getHealthStatus(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/`, { method: "GET" });

  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }

  return res.json();
}

// --------------------
// Natural Language → DB
// --------------------
export async function askNL(question: string): Promise<NLQueryResponse> {
  const res = await fetch(`${BASE_URL}/nl-query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "NL query failed");
  }

  return res.json();
}

