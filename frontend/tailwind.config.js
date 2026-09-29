/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        "primary": "#adc6ff",
        "on-primary": "#002e6a",
        "primary-container": "#4d8eff",
        "on-primary-container": "#00285d",
        "primary-fixed": "#d8e2ff",
        "primary-fixed-dim": "#adc6ff",
        "on-primary-fixed": "#001a42",
        "on-primary-fixed-variant": "#004395",
        "inverse-primary": "#005ac2",

        "secondary": "#4edea3",
        "on-secondary": "#003824",
        "secondary-container": "#00a572",
        "on-secondary-container": "#00311f",
        "secondary-fixed": "#6ffbbe",
        "secondary-fixed-dim": "#4edea3",
        "on-secondary-fixed": "#002113",
        "on-secondary-fixed-variant": "#005236",

        "tertiary": "#ffb95f",
        "on-tertiary": "#472a00",
        "tertiary-container": "#ca8100",
        "on-tertiary-container": "#3e2400",
        "tertiary-fixed": "#ffddb8",
        "tertiary-fixed-dim": "#ffb95f",
        "on-tertiary-fixed": "#2a1700",
        "on-tertiary-fixed-variant": "#653e00",

        "error": "#ffb4ab",
        "on-error": "#690005",
        "error-container": "#93000a",
        "on-error-container": "#ffdad6",

        "surface": "#101418",
        "surface-dim": "#101418",
        "surface-bright": "#363a3e",
        "surface-variant": "#313539",
        "surface-container-lowest": "#0b0f12",
        "surface-container-low": "#181c20",
        "surface-container": "#1c2024",
        "surface-container-high": "#262a2f",
        "surface-container-highest": "#313539",
        "on-surface": "#e0e3e8",
        "on-surface-variant": "#c2c6d6",
        "inverse-surface": "#e0e3e8",
        "inverse-on-surface": "#2d3135",

        "outline": "#8c909f",
        "outline-variant": "#424754",
        "background": "#101418",
        "on-background": "#e0e3e8",
        "surface-tint": "#adc6ff",

        // Legacy compatibility
        workstation: {
          950: '#0b0f12',
          900: '#101418',
          850: '#181c20',
          800: '#1c2024',
          750: '#262a2f',
          700: '#424754',
          600: '#8c909f',
          500: '#c2c6d6',
        }
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        sm: "0.125rem",
        md: "0.25rem",
        lg: "0.25rem",
        xl: "0.5rem",
        full: "0.75rem"
      },
      spacing: {
        "space-xs": "0.125rem",
        "space-sm": "0.25rem",
        "space-md": "0.5rem",
        "space-lg": "0.75rem",
        "space-xl": "1rem",
        "gutter": "0.5rem",
        "margin": "0.5rem"
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
        "headline-lg": ['Inter', 'sans-serif'],
        "headline-md": ['Inter', 'sans-serif'],
        "headline-sm": ['Inter', 'sans-serif'],
        "body-lg": ['Inter', 'sans-serif'],
        "body-md": ['Inter', 'sans-serif'],
        "body-sm": ['Inter', 'sans-serif'],
        "label-md": ['Inter', 'sans-serif'],
        "label-sm": ['JetBrains Mono', 'monospace'],
        "data-lg": ['JetBrains Mono', 'monospace'],
        "data-md": ['JetBrains Mono', 'monospace'],
        "data-sm": ['JetBrains Mono', 'monospace']
      },
      fontSize: {
        "headline-lg": ["20px", { lineHeight: "26px", fontWeight: "600" }],
        "headline-md": ["16px", { lineHeight: "22px", fontWeight: "600" }],
        "headline-sm": ["13px", { lineHeight: "18px", fontWeight: "600" }],
        "body-lg": ["13px", { lineHeight: "18px", fontWeight: "400" }],
        "body-md": ["12px", { lineHeight: "16px", fontWeight: "400" }],
        "body-sm": ["11px", { lineHeight: "14px", fontWeight: "400" }],
        "label-md": ["11px", { lineHeight: "14px", fontWeight: "500" }],
        "label-sm": ["10px", { lineHeight: "12px", fontWeight: "500" }],
        "data-lg": ["14px", { lineHeight: "18px", fontWeight: "500" }],
        "data-md": ["12px", { lineHeight: "16px", fontWeight: "500" }],
        "data-sm": ["11px", { lineHeight: "14px", fontWeight: "400" }]
      }
    },
  },
  plugins: [],
}
