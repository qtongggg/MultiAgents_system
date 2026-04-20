import JobSearchForm from "@/components/JobSearchForm";

export default function JobsPage() {
  return (
    <main className="min-h-screen bg-[#f6f1e8] px-6 py-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="space-y-3">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">
            AI Job Matching
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-stone-900 md:text-5xl">
            Job Search Agent
          </h1>
          <p className="max-w-2xl text-base leading-7 text-stone-600">
            Search AI-related roles, review job summaries, and compare resume
            fit scores in a cleaner card-based experience.
          </p>
        </div>

        <JobSearchForm />
      </div>
    </main>
  );
}