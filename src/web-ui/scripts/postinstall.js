#!/usr/bin/env node

// Post-install script for AI Disk Cleaner Web UI
// This script runs after npm install to ensure everything is set up correctly

const fs = require('fs')
const path = require('path')

console.log('🚀 Setting up AI Disk Cleaner Web UI...')

// Create necessary directories
const directories = [
  'dist',
  'logs',
  'cache',
  'src-tauri/target'
]

directories.forEach(dir => {
  const dirPath = path.join(__dirname, '..', dir)
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true })
    console.log(`✅ Created directory: ${dir}`)
  }
})

// Create .env file if it doesn't exist
const envPath = path.join(__dirname, '..', '.env')
if (!fs.existsSync(envPath)) {
  const envContent = `# AI Disk Cleaner Web UI Environment Variables
# Development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=AI Disk Cleaner
VITE_APP_VERSION=0.2.0

# Tauri
TAURI_PRIVATE_KEY_PATH=./tauri.key
TAURI_PUBLIC_KEY=./tauri.pub

# Development flags
VITE_DEV_MODE=true
VITE_DEBUG=true
`
  fs.writeFileSync(envPath, envContent)
  console.log('✅ Created .env file with defaults')
}

// Check if Tauri CLI is available
try {
  const { execSync } = require('child_process')
  execSync('tauri --version', { stdio: 'pipe' })
  console.log('✅ Tauri CLI is available')
} catch (error) {
  console.log('⚠️  Tauri CLI not found. Install it with: npm install -g @tauri-apps/cli')
}

// Check if Rust is available
try {
  const { execSync } = require('child_process')
  execSync('rustc --version', { stdio: 'pipe' })
  console.log('✅ Rust is available')
} catch (error) {
  console.log('⚠️  Rust not found. Install it from https://rustup.rs/')
}

console.log('✨ AI Disk Cleaner Web UI setup complete!')
console.log('')
console.log('Next steps:')
console.log('  npm run dev       - Start development server')
console.log('  npm run tauri:dev - Start Tauri development mode')
console.log('  npm run build     - Build for production')
console.log('  npm run tauri:build - Build Tauri application')