"use client";

import { useState, useRef } from "react";
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
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const currentQuestion = question.trim();
    setQuestion("");

    try {
      await onSend(currentQuestion);
    } catch (error) {
      console.error("Error sending message:", error);
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
      console.error("Upload error:", error);
      onUploadError(file.name);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  const isDisabled = uploading || loading;

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-3 w-full"
    >
      {/* File Upload Button */}
      <label
        className={`flex h-11 w-11 flex-shrink-0 cursor-pointer items-center justify-center rounded-xl border-2 transition-all duration-200 ${
          isDisabled
            ? "cursor-not-allowed border-[#D3D3D3] bg-[#F9F9F9] text-[#999]"
            : "border-[#E5E5E5] bg-white text-[#2B2B2B] hover:border-[#2B2B2B] hover:bg-[#F8F8F8] active:scale-95"
        }`}
        title={isDisabled ? "Uploading or sending..." : "Upload a PDF"}
      >
        <span className="text-lg font-light select-none">
          {uploading ? "⋯" : "+"}
        </span>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
          disabled={isDisabled}
          aria-label="Upload PDF file"
        />
      </label>

      {/* Text Input */}
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={uploading ? "Uploading PDF..." : "Ask about your document..."}
        disabled={isDisabled}
        className={`flex-1 rounded-xl border-2 px-4 py-2.5 text-[15px] transition-all duration-200 outline-none ${
          isDisabled
            ? "border-[#E5E5E5] bg-[#F9F9F9] text-[#999] cursor-not-allowed"
            : "border-[#E5E5E5] bg-white text-[#2B2B2B] placeholder:text-[#999] focus:border-[#2B2B2B] focus:bg-white hover:border-[#D5D5D5]"
        }`}
        aria-label="Enter your question"
      />

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isDisabled || !question.trim()}
        className={`flex-shrink-0 rounded-xl px-5 py-2.5 font-medium text-white transition-all duration-200 active:scale-95 ${
          isDisabled || !question.trim()
            ? "cursor-not-allowed bg-[#B3B3B3]"
            : "bg-[#2B2B2B] hover:bg-[#1a1a1a]"
        }`}
        aria-label={loading ? "Generating response..." : "Send message"}
      >
        {loading ? (
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-1 h-1 bg-white rounded-full animate-pulse" />
            Generating
          </span>
        ) : (
          "Ask"
        )}
      </button>
    </form>
  );
}