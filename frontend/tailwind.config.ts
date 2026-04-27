import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette for the RAG chat
        neutral: {
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#E5E5E5',
          300: '#D3D3D3',
          500: '#999',
          600: '#666',
          700: '#333',
          900: '#1a1a1a',
        },
      },
      backgroundColor: {
        // Background gradients
        'chat-gradient': 'linear-gradient(to bottom, #FAFAFA, #F5F5F5)',
      },
      animation: {
        bounce: 'bounce 1s infinite',
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      transitionTimingFunction: {
        'in-out-smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      borderRadius: {
        '3xl': '24px',
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: true,
  },
}
export default config