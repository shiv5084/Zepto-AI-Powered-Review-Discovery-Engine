const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const frontendDir = __dirname;

// Check for node_modules dependency folder
const nodeModulesDir = path.join(frontendDir, 'node_modules');
if (!fs.existsSync(nodeModulesDir)) {
  console.log('\x1b[33m[WARN] node_modules not found in frontend directory. Running npm install first...\x1b[0m');
  const installCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  
  try {
    const install = spawn(installCmd, ['install'], {
      cwd: frontendDir,
      stdio: 'inherit',
      shell: true
    });
    
    install.on('close', (code) => {
      if (code === 0) {
        console.log('\x1b[32m[OK] Dependencies installed successfully.\x1b[0m');
        startServer();
      } else {
        console.error(`\x1b[31m[ERROR] Dependency installation failed with code ${code}\x1b[0m`);
        process.exit(code);
      }
    });
  } catch (err) {
    console.error('\x1b[31m[ERROR] Failed to run npm install:\x1b[0m', err.message);
    process.exit(1);
  }
} else {
  startServer();
}

function startServer() {
  // Determine execution mode (dev by default, prod if '--prod' argument is passed)
  const isProd = process.argv.includes('--prod');
  const mode = isProd ? 'build' : 'dev';
  
  console.log(`\x1b[36m[INFO] Starting Next.js frontend in ${isProd ? 'production' : 'development'} mode...\x1b[0m`);
  
  const cmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  
  if (isProd) {
    // For production, we must build the application before starting it
    console.log('\x1b[36m[INFO] Building production bundle...\x1b[0m');
    const build = spawn(cmd, ['run', 'build'], {
      cwd: frontendDir,
      stdio: 'inherit',
      shell: true
    });
    
    build.on('close', (code) => {
      if (code !== 0) {
        console.error(`\x1b[31m[ERROR] Production build failed with code ${code}\x1b[0m`);
        process.exit(code);
      }
      
      console.log('\x1b[36m[INFO] Production build complete. Running production server...\x1b[0m');
      launchProcess(cmd, ['run', 'start']);
    });
  } else {
    launchProcess(cmd, ['run', 'dev']);
  }
}

function launchProcess(cmd, args) {
  const child = spawn(cmd, args, {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: true
  });

  child.on('close', (code) => {
    console.log(`\x1b[36m[INFO] Frontend process exited with code ${code}\x1b[0m`);
    process.exit(code);
  });
  
  // Clean shutdown handling
  const shutDown = () => {
    console.log('\x1b[36m\n[INFO] Shutting down frontend server...\x1b[0m');
    child.kill('SIGINT');
    process.exit(0);
  };
  
  process.on('SIGINT', shutDown);
  process.on('SIGTERM', shutDown);
}
