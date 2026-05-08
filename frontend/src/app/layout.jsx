import { Link2Icon } from "lucide-react";
import "./globals.css";

export const metadata = {
  title: "Sentrya — Manutenção Preditiva",
  description: "Plataforma de monitoramente industrial baseado em IA",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <head>
        <link href="./frontend/src/components/icons" rel="favicon" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-bg-primary font-sans text-brand-cream antialiased">
        {children}
      </body>
    </html>
  );
}
