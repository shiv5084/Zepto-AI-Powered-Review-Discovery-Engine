import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

export async function POST() {
  const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  try {
    const res = await fetch(`${backendUrl}/api/run-pipeline`, {
      method: 'POST',
      cache: 'no-store'
    });

    if (res.ok && res.body) {
      console.log('Connected to FastAPI backend. Streaming pipeline execution logs.');
      return new Response(res.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
        },
      });
    }
  } catch (error) {
    console.warn('FastAPI server offline or unreachable. Falling back to direct filesystem process execution.');
  }

  // 2. Fallback: Run pipeline script directly via child_process.spawn
  const encoder = new TextEncoder();
  const projectRoot = path.resolve(process.cwd(), '..');
  
  let pythonExec = 'python'; // default fallback
  const winVenvPython = path.join(projectRoot, 'venv', 'Scripts', 'python.exe');
  const unixVenvPython = path.join(projectRoot, 'venv', 'bin', 'python');

  if (fs.existsSync(winVenvPython)) {
    pythonExec = winVenvPython;
  } else if (fs.existsSync(unixVenvPython)) {
    pythonExec = unixVenvPython;
  }

  const scriptPath = path.join(projectRoot, 'src', 'main.py');

  if (!fs.existsSync(scriptPath)) {
    return NextResponse.json(
      { error: `Orchestrator script not found at: ${scriptPath} (and FastAPI server is offline)` },
      { status: 500 }
    );
  }

  const stream = new ReadableStream({
    start(controller) {
      const child = spawn(pythonExec, [scriptPath, '--phase', 'all'], {
        cwd: projectRoot,
        env: { 
          ...process.env,
          PYTHONUNBUFFERED: '1'
        },
      });

      child.stdout.on('data', (data) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
          if (line.trim()) {
            controller.enqueue(
              encoder.encode(JSON.stringify({ type: 'stdout', text: line }) + '\n')
            );
          }
        }
      });

      child.stderr.on('data', (data) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
          if (line.trim()) {
            controller.enqueue(
              encoder.encode(JSON.stringify({ type: 'stderr', text: line }) + '\n')
            );
          }
        }
      });

      child.on('close', (code) => {
        controller.enqueue(
          encoder.encode(JSON.stringify({ type: 'close', code }) + '\n')
        );
        controller.close();
      });

      child.on('error', (err) => {
        controller.enqueue(
          encoder.encode(JSON.stringify({ type: 'error', text: err.message }) + '\n')
        );
        controller.close();
      });
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
    },
  });
}

