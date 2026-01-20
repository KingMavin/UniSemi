export default async function authFetch(url, opts = {}) {
  const passcode = localStorage.getItem('admin_passcode');
  
  // Merge headers
  const headers = Object.assign(
    { 'Content-Type': 'application/json' },
    opts.headers || {},
    passcode ? { Authorization: `Passcode ${passcode}` } : {}
  );

  // Setup Timeout Logic
  const controller = new AbortController();
  const id = opts.timeout ? setTimeout(() => controller.abort(), opts.timeout) : null;

  try {
    const res = await fetch(url, Object.assign({}, opts, { headers, signal: controller.signal }));
    
    // Parse response
    const text = await res.text();
    let json = null;
    try { json = text ? JSON.parse(text) : null; } catch { json = null; }

    // Handle HTTP Errors
    if (!res.ok) {
      const errMessage = (json && (json.error || json.message)) || text || res.statusText;
      const e = new Error(errMessage);
      e.status = res.status;
      // Mimic axios response structure for compatibility
      e.response = { status: res.status, data: json || text }; 
      throw e;
    }

    return json ?? {};

  } catch (error) {
    // Handle Timeout specifically
    if (error.name === 'AbortError') {
      const timeoutError = new Error('Request timed out');
      timeoutError.response = { status: 408, data: { message: 'Request timed out' } };
      throw timeoutError;
    }
    throw error;
  } finally {
    if (id) clearTimeout(id);
  }
}