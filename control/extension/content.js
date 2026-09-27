// Always-visible escape hatch so a room user can get back to the home
// screen from any state Teams' own UI is in, per CLAUDE.md's flow: "A
// small, always-available Leave & Home control is injected into the
// Teams page".
(function () {
  const BUTTON_ID = 'openroom-leave-and-home';

  function injectButton() {
    if (document.getElementById(BUTTON_ID)) return;

    const button = document.createElement('button');
    button.id = BUTTON_ID;
    button.type = 'button';
    button.textContent = 'Leave & Home';
    Object.assign(button.style, {
      position: 'fixed',
      bottom: '16px',
      right: '16px',
      zIndex: '2147483647',
      padding: '0.75rem 1.5rem',
      fontSize: '1rem',
      fontFamily: 'system-ui, sans-serif',
      background: '#dc2626',
      color: '#ffffff',
      border: 'none',
      borderRadius: '0.5rem',
      cursor: 'pointer',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
    });
    button.addEventListener('click', () => {
      button.disabled = true;
      chrome.runtime.sendMessage({ type: 'openroom-leave-and-home' }, () => {
        button.disabled = false;
      });
    });

    document.body.appendChild(button);
  }

  injectButton();
  // Teams is a single-page app that can tear down and rebuild the body;
  // keep the button present across those re-renders.
  new MutationObserver(injectButton).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
