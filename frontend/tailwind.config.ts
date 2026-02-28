import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--bg-primary)",
                foreground: "var(--text-primary)",
                wabi: {
                    bg: "#f4f4f0", // off-white
                    text: "#1a1a1a", // dark text for high contrast
                    accent: "#2f2f2f",
                }
            },
            fontFamily: {
                sans: ["var(--font-inter)", "sans-serif"],
                serif: ["var(--font-serif)", "serif"],
            },
        },
    },
    plugins: [],
};
export default config;
