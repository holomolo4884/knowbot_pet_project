"use client";

import { useRef, useState } from "react";
import { ALLOWED_EXT, MAX_SIZE_MB } from "@/lib/upload-types";

interface DropzoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function Dropzone({ onFile, disabled }: DropzoneProps) {
  const [over, setOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition ${
        over
          ? "border-blue-500 bg-blue-50"
          : "border-slate-300 bg-white hover:border-slate-400"
      } ${disabled ? "pointer-events-none opacity-50" : ""}`}
    >
      <div className="mb-3 text-4xl">📄</div>
      <div className="font-medium text-slate-800">
        Перетащите документ сюда или нажмите для выбора
      </div>
      <div className="mt-1 text-sm text-slate-500">
        {ALLOWED_EXT.join(", ")} · до {MAX_SIZE_MB} МБ
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_EXT.join(",")}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}