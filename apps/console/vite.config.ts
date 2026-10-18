import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
export default defineConfig({base:process.env.VITE_BASE || './',plugins:[react(),tailwind()],build:{chunkSizeWarningLimit:1200},server:{proxy:{'/api':{target:'http://127.0.0.1:8000',rewrite:p=>p.replace(/^\/api/,'')}}}});
