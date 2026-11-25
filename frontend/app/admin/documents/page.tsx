 import Link from "next/link";
import { DocumentsList } from "@/components/admin/documents-list";

export default function AdminDocumentsPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-4 p-8">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Документы</h1>
          <p className="text-sm text-slate-500">
            Список загруженных документов. Переименование — клик по названию.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/admin/upload"
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Загрузить
          </Link>
          <Link
            href="/"
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            ← К чату
          </Link>
        </div>
      </header>
      <DocumentsList />
    </main>
  );
}