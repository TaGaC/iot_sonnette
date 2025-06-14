self.addEventListener('push', event => {
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/static/icon.png'
    })
  );
});




// A mettre dans l'index
if ('serviceWorker' in navigator && 'PushManager' in window) {
  navigator.serviceWorker.register('/static/sw.js').then(swReg => {
    swReg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: '<ta_clé_publique_VAPID_convertie_en_base64>'
    }).then(subscription => {
      fetch('/api/subscribe', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(subscription)
      });
    });
  });
}