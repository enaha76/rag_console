import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadDocument, listDocuments } from "@/lib/api";

interface ServerDoc {
  id: string;
  original_filename: string;
  status?: string;
  file_size?: number;
  processed_chunks?: number;
  total_chunks?: number;
  language?: string;
  uploaded_at?: string;
  processed_at?: string | null;
  word_count?: number;
  tags?: string[];
  page_count?: number;
}

const ACCEPTED = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export default function DocumentsPage() {
  const [dragOver, setDragOver] = useState(false);
  const [docs, setDocs] = useState<ServerDoc[]>([]);
  const [loading, setLoading] = useState(false); // upload in progress
  const [listLoading, setListLoading] = useState(false); // fetching documents
  const [filter, setFilter] = useState<"all" | "pending" | "processed">("all");
  const inputRef = useRef<HTMLInputElement>(null);

  function onBrowseClick() {
    inputRef.current?.click();
  }

  function validate(file: File) {
    if (
      !ACCEPTED.includes(file.type) &&
      !/\.(pdf|txt|docx)$/i.test(file.name)
    ) {
      throw new Error("Unsupported file type");
    }
    const MAX = 20 * 1024 * 1024; // 20MB
    if (file.size > MAX) throw new Error("File too large (20MB limit)");
  }

  async function refreshList() {
    setListLoading(true);
    try {
      const res = await listDocuments(0, 20);
      setDocs(res.documents || []);
    } catch (e) {
      // ignore list errors for now
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    refreshList();
  }, []);

  async function handleFiles(fileList: FileList | null) {
    if (!fileList) return;
    const files = Array.from(fileList);
    setLoading(true);
    try {
      for (const file of files) {
        try {
          validate(file);
          await uploadDocument(file, { title: file.name });
        } catch (e) {
          // You can surface a toast here
        }
      }
      await refreshList();
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  const shown = docs.filter((d) =>
    filter === "all" ? true : (d.status || "").toLowerCase() === filter,
  );

  return (
    <div className="max-w-5xl mx-auto p-4 lg:p-8">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-slate-600">Filter</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="border rounded-md px-2 py-1 text-sm"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="processed">Processed</option>
          </select>
        </div>
      </div>

      <div
        className={`rounded-2xl border-2 border-dashed ${dragOver ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white"} p-8 text-center text-slate-600 cursor-pointer`}
        onClick={onBrowseClick}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="font-medium">Drag & drop files here</div>
        <div className="text-sm">
          or click to choose (pdf, txt, docx). Max 20MB per file.
        </div>
        <div className="mt-4 flex justify-center items-center gap-2">
          <Button className="bg-blue-600 hover:bg-blue-500 text-white" disabled={loading}>
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                </svg>
                Uploading...
              </span>
            ) : (
              "Choose files"
            )}
          </Button>
        </div>
      </div>

      <div className="mt-6 space-y-3 min-h-[80px]">
        {listLoading ? (
          <div className="flex items-center gap-2 text-slate-600 text-sm">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
            </svg>
            Loading documents…
          </div>
        ) : shown.length === 0 ? (
          <div className="text-sm text-slate-500">No documents yet.</div>
        ) : (
          shown.map((d) => (
            <div
              key={d.id}
              className="rounded-xl border bg-white p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-800 truncate">
                  {d.original_filename}
                </div>
                <div className="text-xs text-slate-500">
                  {(Number(d.file_size || 0) / 1024).toFixed(1)} KB
                </div>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded-full border ${d.status === "processed" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : d.status === "pending" ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-slate-50 text-slate-700 border-slate-200"}`}
              >
                {d.status || "unknown"}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
