import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Bebas_Neue } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

const bebasNeue = Bebas_Neue({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-brand",
});

export const metadata: Metadata = {
  title: "AegisCloud — DevSecOps Sentinel",
  description:
    "Zero-Trust AI Agent Dashboard for Infrastructure Security. Powered by Auth0 Token Vault, CIBA & RAR.",
  keywords: [
    "DevSecOps",
    "AI Agent",
    "Auth0",
    "Token Vault",
    "CIBA",
    "Zero Trust",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`dark ${inter.variable} ${jetbrains.variable} ${bebasNeue.variable}`}
    >
      <body className="min-h-screen antialiased">
        <Providers>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-col flex-1 overflow-hidden">
              <Header />
              <main className="flex-1 overflow-y-auto p-8">{children}</main>
            </div>
          </div>
        </Providers>
        {/* Remove the tw-animate-css blue glow overlay */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function killGlow() {
                var el = document.getElementById('preact-border-shadow-host');
                if (el) { el.remove(); return; }
                setTimeout(killGlow, 200);
              })();
            `,
          }}
        />
      </body>
    </html>
  );
}
