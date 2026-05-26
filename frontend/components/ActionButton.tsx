import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "outline" | "danger";

const styles: Record<Variant, string> = {
  primary: "border-slate-950 bg-slate-950 text-white hover:bg-slate-800",
  secondary: "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
  outline: "border-indigo-200 bg-indigo-50 text-indigo-800 hover:bg-indigo-100",
  danger: "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
};

const base = "inline-flex h-10 items-center justify-center rounded-2xl border px-3.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";

export function ActionButton({
  children,
  variant = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button className={`${base} ${styles[variant]} ${className}`} {...props}>{children}</button>;
}

export function ActionLink({ children, href, variant = "secondary", className = "" }: { children: ReactNode; href: string; variant?: Variant; className?: string }) {
  return <Link href={href} className={`${base} ${styles[variant]} ${className}`}>{children}</Link>;
}
