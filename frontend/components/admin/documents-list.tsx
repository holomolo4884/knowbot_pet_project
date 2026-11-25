"use client";

import { useEffect, useState } from "react";
import {
  deleteDocument,
  listDocuments,
  reindexDocument,
  renameDocument,
  type DocumentListItem,
} from "@/lib/admin-api";
import { ConfirmButton } from "./confirm-button";

type SortKey = "title" | "file_type" | "chunks" | "created_at" | "file_size";
type SortDir = "asc" | "desc";

interface Toast {
  id: string;
  kind: "success" | "error";
  message: string;
}

export function DocumentsList() {
  const [items, setItems] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [reindexing, setReindexing] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [toasts, setToasts] = useState<Toast[]>([]);

  const pushToast = (kind: "success" | "error", message: string) => {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000);
  };

  const refresh = async () => {
    try {
      setError(null);
      const data = await listDocuments();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleRenameStart = (item: DocumentListItem) => {
    setEditingId(item.doc_id);
    setDraftTitle(item.title);
  };

  const handleRenameCommit = async () => {
    if (!editingId) return;
    const trimmed = draftTitle.trim();
    if (!trimmed) {
      pushToast("error", "Название не может быть пустым");
      setEditingId(null);
      return;
    }
    const current = items.find((i) => i.doc_id === editingId);
    if (!current || current.title === trimmed) {
      setEditingId(null);
      return;
    }
    try {
      const updated = await renameDocument(editingId, trimmed);
      setItems((prev) => prev.map((x) => (x.doc_id === updated.doc_id ? updated : x)));
      pushToast("success", "Переименовано");
    } catch (e) {
      pushToast("error", e instanceof Error ? e.message : "Ошибка переименования");
    } finally {
      setEditingId(null);
    }
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleRenameCommit();
    if (e.key === "Escape") setEditingId(null);
  };

  const handleDelete = async (docId: string, title: string) => {
    try {
      await deleteDocument(docId);
      setItems((prev) => prev.filter((x) => x.doc_id !== docId));
      pushToast("success", `«${title}» удалён`);
    } catch (e) {
      pushToast("error", e instanceof Error ? e.message : "Ошибка удаления");
    }
  };

  const handleReindex = async (item: DocumentListItem) => {
    setReindexing((s) => new Set(s).add(item.doc_id));
    try {
      const res = await reindexDocument(item.doc_id);
      pushToast("success", `Переиндексирован: ${res.chunks} чанков за ${res.took_ms.toFixed(0)} мс`);
      await refresh();
    } catch (e) {
      pushToast("error", e instanceof Error ? e.message : "Ошибка переиндексации");
    } finally {
      setReindexing((s) => {
        const next = new Set(s);
        next.delete(item.doc_id);
        return next;
      });
    }
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sorted = [...items].sort((a, b) => {
    const av = a[sortKey] ?? "";
    const bv = b[sortKey] ?? "";
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const arrow = (key: SortKey) => (sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : "");

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <>
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          Ошибка загрузки: {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th
                onClick={() => toggleSort("title")}
                className="cursor-pointer px-4 py-2.5 text-left font-medium text-slate-600 hover:bg-slate-100"
              >
                Название{arrow("title")}
              </th>
              <th
                onClick={() => toggleSort("file_type")}
                className="cursor-pointer px-4 py-2.5 text-left font-medium text-slate-600 hover:bg-slate-100"
              >
                Тип{arrow("file_type")}
              </th>
              <th
                onClick={() => toggleSort("chunks")}
                className="cursor-pointer px-4 py-2.5 text-right font-medium text-slate-600 hover:bg-slate-100"
              >
                Чанков{arrow("chunks")}
              </th>
              <th
                onClick={() => toggleSort("file_size")}
                className="cursor-pointer px-4 py-2.5 text-right font-medium text-slate-600 hover:bg-slate-100"
              >
                Размер{arrow("file_size")}
              </th>
              <th
                onClick={() => toggleSort("created_at")}
                className="cursor-pointer px-4 py-2.5 text-left font-medium text-slate-600 hover:bg-slate-100"
              >
                Создан{arrow("created_at")}
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-slate-600">
                Статус
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-slate-600">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  Загрузка…
                </td>
              </tr>
            )}
            {!loading && sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  Документов пока нет. Загрузите через страницу «Загрузка».
                </td>
              </tr>
            )}
            {sorted.map((item) => {
              const isEditing = editingId === item.doc_id;
              const isReindexing = reindexing.has(item.doc_id);
              return (
                <tr key={item.doc_id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5">
                    {isEditing ? (
                      <input
                        autoFocus
                        type="text"
                        value={draftTitle}
                        onChange={(e) => setDraftTitle(e.target.value)}
                        onBlur={handleRenameCommit}
                        onKeyDown={handleRenameKeyDown}
                        className="w-full rounded border border-blue-400 bg-white px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-blue-100"
                      />
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleRenameStart(item)}
                        className="text-left font-medium text-slate-800 hover:text-blue-700"
                        title="Кликните для переименования"
                      >
                        {item.title}
                      </button>
                    )}
                    <div className="truncate font-mono text-[10px] text-slate-400">
                      {item.content_hash.slice(0, 12)}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">
                      {item.file_type ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-700">
                    {item.chunks}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-600">
                    {item.file_size ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="px-4 py-2.5">
                    {item.stored ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                        <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                        исходник есть
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700" title="Исходный файл недоступен — загрузите документ заново">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                        нет исходника
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => handleReindex(item)}
                        disabled={!item.stored || isReindexing}
                        className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
                        title={
                          !item.stored
                            ? "Исходник недоступен — загрузите документ заново"
                            : "Пересобрать чанки текущим парсером"
                        }
                      >
                        {isReindexing ? "…" : "Переиндексировать"}
                      </button>
                      <ConfirmButton
                        label="Удалить"
                        prompt={`Удалить «${item.title}»? Чанки и файл будут удалены безвозвратно.`}
                        onConfirm={() => handleDelete(item.doc_id, item.title)}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Toasts */}
      <div className="pointer-events-none fixed bottom-6 right-6 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto rounded-md px-4 py-2 text-sm shadow-lg ${
              t.kind === "success"
                ? "bg-green-600 text-white"
                : "bg-red-600 text-white"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </>
  );
}