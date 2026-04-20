"use client";

import { useState } from "react";
import { uploadPdf } from "@/lib/api";

type RagQueryFormProps = {
  onSend: (question: string) => Promise<void>;
  loading: boolean;
  onUploadStart: (fileName: string) => void;
  onUploadSuccess: (fileName: string, fileUrl: string) => void;
  onUploadError: (fileName: string) => void;
};

export default function RagQueryForm({
  onSend,
  loading,
  onUploadStart,
  onUploadSuccess,
  onUploadError,
}: RagQueryFormProps) {
  const [question, setQuestion] = useState("");
  const [uploading, setUploading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    const currentQuestion = question.trim();
    setQuestion("");

    try {
      await onSend(currentQuestion);
    } catch (error) {
      console.error(error);
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    onUploadStart(file.name);

    try {
      setUploading(true);
      await uploadPdf(file);

      const fileUrl = URL.createObjectURL(file);
      onUploadSuccess(file.name, fileUrl);
    } catch (error) {
      console.error(error);
      onUploadError(file.name);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-3">
      <label className="flex h-12 w-12 shrink-0 cursor-pointer items-center justify-center rounded-2xl border border-[#B3B3B3] bg-[#FFFFFF] text-xl text-[#2B2B2B] shadow-sm transition hover:bg-[#F3F3F3]">
        {uploading ? "…" : "+"}
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
          disabled={uploading || loading}
        />
      </label>

      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask something about your PDF..."
        className="flex-1 rounded-2xl border border-[#B3B3B3] bg-[#FFFFFF] px-4 py-3 text-[#2B2B2B] placeholder:text-[#8A8A8A] outline-none transition focus:border-[#2B2B2B]"
      />

      <button
        type="submit"
        disabled={loading}
        className="shrink-0 rounded-2xl bg-[#2B2B2B] px-5 py-3 font-medium text-white shadow-sm transition hover:opacity-90 disabled:opacity-50"
      >
        {loading ? "Generating..." : "Ask"}
      </button>
    </form>
  );
}