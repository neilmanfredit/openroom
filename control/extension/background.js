// Runs the actual network request: a background service worker's fetches
// are covered by this extension's host_permissions and aren't subject to
// the Teams page's own CORS/CSP, unlike a fetch from the content script.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'openroom-leave-and-home') {
    return undefined;
  }
  fetch('http://127.0.0.1:8080/api/home', { method: 'POST' })
    .then(() => sendResponse({ ok: true }))
    .catch(() => sendResponse({ ok: false }));
  return true; // keep the message channel open for the async response
});
