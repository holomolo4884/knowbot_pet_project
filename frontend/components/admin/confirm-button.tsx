"use client";

import { useState } from "react";

interface ConfirmButtonProps {
  label: string;
  confirmLabel?: string;
  cancelLabel?: string;
  prompt: string;
  onConfirm: () => Promise<void> | void;
  disabled?: boolean;
  variant?: "danger" | "primary";
}

export function ConfirmButton({
  label,
  confirmLabel = "Да, удалить",
  cancelLabel = "Отмена",
  prompt,
  onConfirm,
  disabled,
  variant = "danger",
}: ConfirmButtonProps) {
  const [pending, setPending] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const handleClick = async () => {
    if (confirming) {
      setPending(true);
      try {
        await onConfirm();
      } finally {
        setPending(false);
        setConfirming(false);
      }
    } else {
      // eslint-disable-next-line no-alert
      if (window.confirm(prompt)) {
        setPending(true);
        try {
          await onConfirm();
        } finally {
          setPending(false);
        }
      }
    }
  };

  const baseClass =
    "shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition disabled:opacity-40";
  const variantClass =
    variant === "danger"
      ? "bg-red-50 text-red-700 hover:bg-red-100"
      : "bg-slate-100 text-slate-700 hover:bg-slate-200";

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || pending}
      className={`${baseClass} ${variantClass}`}
    >
      {pending ? "…" : label}
    </button>
  );
}