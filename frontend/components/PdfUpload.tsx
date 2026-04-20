"use client";

import { useState } from "react";
import { uploadPdf } from "@/lib/api";

export default function PdfUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    try {
      setLoading(true);
      setMessage("");
      const result = await uploadPdf(file);
      setMessage(result.message || "PDF uploaded successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleUpload}
      className="rounded-2xl bg-blue-500 p-6 shadow space-y-4"
    >
      <h2 className="text-xl font-semibold">Upload PDF</h2>

      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="block w-full"
      />

      <button
        type="submit"
        disabled={!file || loading}
        className="rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50"
      >
        {loading ? "Uploading..." : "Upload"}
      </button>

      {message && <p className="text-sm text-gray-700">{message}</p>}
    </form>
  );
}