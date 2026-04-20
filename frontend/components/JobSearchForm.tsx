"use client";

import { useState } from "react";
import { searchJobs } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";

type Job = {
  title: string;
  company: string;
  location: string;
  brief_summary?: string;
  fit_score?: number;
  matching_skills?: string[];
  missing_skills?: string[];
  reason?: string;
  link?: string;
};

export default function JobSearchForm() {
  const [keyword, setKeyword] = useState("AI Engineer");
  const [location, setLocation] = useState("Malaysia");
  const [perPage, setPerPage] = useState(5);
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    try {
      setLoading(true);
      setError("");
      setJobs([]);

      const data = await searchJobs({
        keyword,
        location,
        per_page: perPage,
      });

      const sortedJobs = [...(data.result.jobs || [])].sort(
        (a, b) => (b.fit_score || 0) - (a.fit_score || 0)
      );

      setJobs(sortedJobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search jobs");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-[28px] border border-stone-200 bg-[#fffaf3] p-6 shadow-[0_10px_40px_rgba(120,100,80,0.08)] md:p-8">
      <div className="mb-6 flex flex-col gap-2">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-stone-500">
          Search Roles
        </p>
        <h2 className="text-2xl font-semibold text-stone-900">
          Find your best-fit jobs
        </h2>
        <p className="max-w-2xl text-sm leading-6 text-stone-600">
          Enter a role, location, and result count. Your jobs will be ranked by
          resume match score and displayed in a swipeable carousel.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-3">
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Job title"
          className="rounded-2xl border border-stone-200 bg-white px-4 py-3 text-stone-800 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-200"
        />

        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Location"
          className="rounded-2xl border border-stone-200 bg-white px-4 py-3 text-stone-800 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-200"
        />

        <input
          type="number"
          min={1}
          max={10}
          value={perPage}
          onChange={(e) => setPerPage(Number(e.target.value))}
          className="rounded-2xl border border-stone-200 bg-white px-4 py-3 text-stone-800 shadow-sm outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-stone-200"
        />

        <button
          type="submit"
          disabled={loading}
          className="md:col-span-3 rounded-2xl bg-stone-900 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-stone-800 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search Jobs"}
        </button>
      </form>

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </p>
      )}

      {!loading && jobs.length > 0 && (
        <div className="mt-8">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-stone-700">
                {jobs.length} job{jobs.length > 1 ? "s" : ""} found
              </p>
              <p className="text-sm text-stone-500">
                Ranked by highest resume match first
              </p>
            </div>
          </div>

          <Carousel className="mx-auto w-full max-w-4xl">
            <CarouselContent>
              {jobs.map((job, index) => {
                const fitScore = job.fit_score || 0;
                const percentage = Math.round(fitScore * 100);

                return (
                  <CarouselItem key={index}>
                    <div className="p-1">
                      <Card className="overflow-hidden rounded-[26px] border border-stone-200 bg-white shadow-[0_8px_30px_rgba(120,100,80,0.08)]">
                        <CardContent className="p-0">
                          <div className="border-b border-stone-100 bg-[#fcf6ec] px-6 py-5">
                            <div className="mb-3 flex flex-wrap items-center gap-2">
                              <span className="rounded-full bg-stone-900 px-3 py-1 text-xs font-medium text-white">
                                Job {index + 1}
                              </span>
                              {index === 0 && (
                                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                                  Best Match
                                </span>
                              )}
                            </div>

                            <h3 className="text-2xl font-semibold tracking-tight text-stone-900">
                              {job.title}
                            </h3>

                            <p className="mt-2 text-sm text-stone-600">
                              {job.company} • {job.location}
                            </p>
                          </div>

                          <div className="space-y-5 px-6 py-6">
                            {job.brief_summary && (
                              <p className="text-sm leading-7 text-stone-700">
                                {job.brief_summary}
                              </p>
                            )}

                            {fitScore > 0 && (
                              <div className="rounded-2xl border border-stone-200 bg-[#f8f1e7] p-4">
                                <div className="mb-2 flex items-center justify-between">
                                  <p className="text-sm font-semibold text-stone-800">
                                    Resume Match
                                  </p>
                                  <p className="text-sm font-bold text-stone-900">
                                    {percentage}%
                                  </p>
                                </div>

                                <div className="h-3 w-full rounded-full bg-stone-200">
                                  <div
                                    className="h-3 rounded-full bg-stone-800 transition-all"
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>

                                {!!job.matching_skills?.length && (
                                  <p className="mt-4 text-sm leading-6 text-emerald-700">
                                    <span className="font-medium">Matching:</span>{" "}
                                    {job.matching_skills.join(", ")}
                                  </p>
                                )}

                                {!!job.missing_skills?.length && (
                                  <p className="mt-2 text-sm leading-6 text-rose-700">
                                    <span className="font-medium">Missing:</span>{" "}
                                    {job.missing_skills.join(", ")}
                                  </p>
                                )}

                                {job.reason && (
                                  <p className="mt-3 text-sm leading-6 text-stone-600">
                                    {job.reason}
                                  </p>
                                )}
                              </div>
                            )}

                            {job.link && (
                              <a
                                href={job.link}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center rounded-2xl border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 transition hover:bg-stone-50"
                              >
                                Apply here
                              </a>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </CarouselItem>
                );
              })}
            </CarouselContent>

            {jobs.length > 1 && (
              <>
                <CarouselPrevious className="left-2 border-stone-300 bg-white text-stone-800 shadow-md hover:bg-stone-50" />
                <CarouselNext className="right-2 border-stone-300 bg-white text-stone-800 shadow-md hover:bg-stone-50" />
              </>
            )}
          </Carousel>
        </div>
      )}
    </div>
  );
}