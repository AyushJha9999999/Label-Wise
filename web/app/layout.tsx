import type { Metadata } from "next";
import { AuthProvider } from "@/lib/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "LabelWise — Know what’s in your food",
  description: "A clear, careful way to check food labels against your dietary needs.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body data-theme="dark"><AuthProvider>{children}</AuthProvider></body></html>;
}
