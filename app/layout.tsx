import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alcantara Studio AI Video",
  description: "Laboratório de criação de vídeos musicais do Alcantara Studio."
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
