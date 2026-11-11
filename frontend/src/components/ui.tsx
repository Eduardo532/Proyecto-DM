import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "danger" | "subtle";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-gold text-ink hover:bg-[#d8b25c] font-semibold",
  ghost: "border border-line text-parchment hover:border-gold hover:text-gold",
  danger: "bg-blood text-parchment hover:bg-[#bf3434]",
  subtle: "text-parchment-dim hover:text-gold",
};

export function Button({
  variant = "ghost",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`rounded-md px-3 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-40 ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

export function Panel({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-ink-2/90 shadow-lg shadow-black/30 ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-2 border-b border-line px-4 py-2">
          <h2 className="font-display text-sm uppercase text-gold">{title}</h2>
          <div className="flex items-center gap-2">{actions}</div>
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const inputClass =
  "w-full rounded-md border border-line bg-ink px-3 py-1.5 text-parchment placeholder:text-parchment-dim/50 focus:border-gold focus:outline-none";

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-parchment-dim">{label}</span>
      {children}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className ?? ""}`} />;
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${inputClass} ${props.className ?? ""}`} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputClass} ${props.className ?? ""}`} />;
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "gold" | "blood" | "moss" | "arcane" }) {
  const tones = {
    default: "border-line text-parchment-dim",
    gold: "border-gold-dim text-gold",
    blood: "border-blood text-[#e07a7a]",
    moss: "border-moss text-[#a9c78d]",
    arcane: "border-arcane text-[#aab6e6]",
  };
  return <span className={`inline-block rounded border px-1.5 py-0.5 text-xs ${tones[tone]}`}>{children}</span>;
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return <p className="text-sm text-[#e07a7a]">{message}</p>;
}

export function HpBar({ current, max, temp = 0 }: { current: number; max: number; temp?: number }) {
  const ratio = max > 0 ? Math.max(0, Math.min(1, current / max)) : 0;
  const color = ratio > 0.5 ? "bg-moss" : ratio > 0.25 ? "bg-gold" : "bg-blood";
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="h-2 flex-1 overflow-hidden rounded bg-ink-3">
        <div className={`h-full ${color}`} style={{ width: `${ratio * 100}%` }} />
      </div>
      <span className="tabular-nums text-parchment-dim">
        {current}/{max}
        {temp > 0 ? ` +${temp}` : ""}
      </span>
    </div>
  );
}

export function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true">
      <div className={`max-h-[90vh] w-full overflow-auto rounded-lg border border-line bg-ink-2 shadow-2xl scroll-thin ${wide ? "max-w-5xl" : "max-w-lg"}`}>
        <header className="sticky top-0 flex items-center justify-between border-b border-line bg-ink-2 px-4 py-3">
          <h2 className="font-display text-gold">{title}</h2>
          <Button variant="subtle" onClick={onClose} aria-label="Cerrar">
            ✕
          </Button>
        </header>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm italic text-parchment-dim">{children}</p>;
}
