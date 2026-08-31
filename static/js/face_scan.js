/* Home-page camera scan: click-to-capture, not continuous live scanning --
 * the face engine is a several-second subprocess call per photo (see
 * recognition/face_engine.py), so streaming frames to it isn't feasible.
 * One button press -> one still frame -> one identify request. */
(function () {
  var video = document.getElementById('scan-video');
  var canvas = document.getElementById('scan-canvas');
  var startBtn = document.getElementById('start-camera-btn');
  var scanBtn = document.getElementById('scan-btn');
  var statusEl = document.getElementById('scan-status');
  var confirmEl = document.getElementById('scan-confirm');
  var confirmName = document.getElementById('scan-confirm-name');
  var confirmYes = document.getElementById('scan-confirm-yes');
  var confirmNo = document.getElementById('scan-confirm-no');
  var csrfInput = document.querySelector('input[name=csrfmiddlewaretoken]');

  if (!scanBtn) return; // scan panel isn't on this page
  var identifyUrl = scanBtn.dataset.identifyUrl;
  var stream = null;

  function setStatus(message, kind) {
    if (!statusEl) return;
    statusEl.hidden = !message;
    statusEl.textContent = message || '';
    statusEl.className = 'scan-status' + (kind ? ' scan-status--' + kind : '');
  }

  function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus('This browser does not support camera access. Use Search manually or Print without an account instead.', 'error');
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } }).then(function (mediaStream) {
      stream = mediaStream;
      video.srcObject = stream;
      startBtn.hidden = true;
      scanBtn.disabled = false;
      setStatus('');
    }).catch(function (err) {
      setStatus('Could not access the camera: ' + err.message, 'error');
    });
  }

  function scanFace() {
    confirmEl.hidden = true;
    scanBtn.disabled = true;
    setStatus('Scanning… this can take a few seconds.', 'info');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    canvas.toBlob(function (blob) {
      var formData = new FormData();
      formData.append('photo', blob, 'scan.jpg');

      fetch(identifyUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfInput.value },
        body: formData,
      }).then(function (response) {
        return response.json();
      }).then(function (data) {
        scanBtn.disabled = false;
        if (data.error) {
          setStatus(data.error, 'error');
          return;
        }
        if (data.matched) {
          setStatus('');
          confirmName.textContent = data.resident_name;
          confirmYes.href = data.issue_url;
          confirmEl.hidden = false;
        } else {
          setStatus('No match found. Try again, or use Search manually / Print without an account below.', 'error');
        }
      }).catch(function (err) {
        scanBtn.disabled = false;
        setStatus('Face recognition request failed: ' + err.message, 'error');
      });
    }, 'image/jpeg', 0.9);
  }

  startBtn.addEventListener('click', startCamera);
  scanBtn.addEventListener('click', scanFace);
  if (confirmNo) {
    confirmNo.addEventListener('click', function () { confirmEl.hidden = true; });
  }
})();
