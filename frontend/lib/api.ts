const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8001";

export async function uploadPdf(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/rag/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Failed to upload PDF");
  }

  return res.json();
}

export async function askRagQuestion(question: string, top_k: number) {
  console.log("API_BASE_URL =", API_BASE_URL);
  console.log("Calling URL =", `${API_BASE_URL}/api/rag/query`);

  const start = performance.now();

  const res = await fetch(`${API_BASE_URL}/api/rag/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, top_k }),
  });

  console.log("Fetch took", ((performance.now() - start) / 1000).toFixed(2), "s");

  if (!res.ok) {
    throw new Error("Failed to get RAG answer");
  }

  const data = await res.json();
  console.log("Response JSON =", data);

  return data;
}

export async function searchJobs(payload: {
  keyword: string;
  location: string;
  per_page: number;
}) {
  const res = await fetch(`${API_BASE_URL}/api/jobs/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to search jobs");
  }

  return res.json();
}


export async function searchResume(question: string, top_k: number) {
  const res = await fetch(`${API_BASE_URL}/api/jobs/resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, top_k }),
  });

  if (!res.ok) {
    throw new Error("Failed to get resume response");
  }

  return res.json();
}