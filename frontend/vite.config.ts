import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({plugins:[react()],server:{port:5178,proxy:{'/api':'http://127.0.0.1:8018','/docs':'http://127.0.0.1:8018','/openapi.json':'http://127.0.0.1:8018'}},build:{sourcemap:true}})
