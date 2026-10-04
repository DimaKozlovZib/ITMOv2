// check-after-edit.js
// Opencode plugin: after successful file edits, run Practice 4 smoke checks.
// Auto-discovered from .opencode/plugins/ — no config changes required.

const { spawn } = require('child_process')
const { existsSync } = require('fs')
const { join } = require('path')

/**
 * Execute a command and capture output.
 * @param {string} cmd
 * @param {string[]} args
 * @param {{cwd?: string, env?: Record<string,string|undefined>}} [opts]
 * @returns {Promise<{ code: number, stdout: string, stderr: string }>} 
 */
function exec(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { cwd: opts.cwd, env: opts.env, shell: false, windowsHide: true })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d) => (stdout += d.toString()))
    child.stderr.on('data', (d) => (stderr += d.toString()))
    child.on('close', (code) => resolve({ code: code ?? 0, stdout, stderr }))
  })
}

module.exports = async ({ directory }) => {
  // Debounce sequential edit operations within a short window
  let pending = Promise.resolve()

  async function runCheck() {
    const root = directory
    const script = join(root, 'scripts', 'check_practice4.py')
    if (!existsSync(script)) {
      console.log('[check-after-edit] Skip: scripts/check_practice4.py not found')
      return
    }

    // Prefer venv Python on Windows; fallback to system python
    const pyVenvWin = join(root, '.venv', 'Scripts', 'python.exe')
    const pyVenvNix = join(root, '.venv', 'bin', 'python')
    const python = existsSync(pyVenvWin) ? pyVenvWin : (existsSync(pyVenvNix) ? pyVenvNix : 'python')

    console.log('[check-after-edit] Running smoke checks for Practice 4...')
    const { code, stdout, stderr } = await exec(python, [script], { cwd: root })
    if (stdout.trim()) console.log(stdout.trim())
    if (stderr.trim()) console.warn(stderr.trim())
    if (code !== 0) {
      console.warn(`[check-after-edit] Smoke checks failed with code ${code}`)
    } else {
      console.log('[check-after-edit] Smoke checks passed')
    }
  }

  return {
    // Trigger after edits are applied
    'tool.execute.after': async (input, output) => {
      try {
        const name = String(input?.name || input?.tool || '').toLowerCase()
        // Heuristic: run after file-editing tools
        const isEdit = name.includes('edit') || name.includes('apply_patch') || name.includes('apply-patch')
        if (!isEdit) return

        // Serialize runs to avoid overlap
        pending = pending.then(runCheck, runCheck)
        await pending
      } catch (e) {
        console.warn('[check-after-edit] Error while running checks:', e && e.message ? e.message : e)
      }
    },
  }
}
