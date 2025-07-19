document.addEventListener("DOMContentLoaded", () => {
  const blobs = document.querySelectorAll(".blob");
  const styleSheet = document.createElement("style");
  document.head.appendChild(styleSheet);

  const blobData = [];

  const sizeToBlur = size => (40 + ((size - 80) / 70) * 35);

  blobs.forEach((blob, index) => {
    // Random base size
    const baseSize = Math.floor(Math.random() * 70) + 80;  // 80–150
    const maxSize = baseSize + 50;                         // 130–200
    const baseBlur = sizeToBlur(baseSize);
    const maxBlur = sizeToBlur(maxSize);

    // Set initial position
    const width = baseSize;
    const height = baseSize;
    const x = Math.random() * (window.innerWidth - width);
    const y = Math.random() * (window.innerHeight - height);

    // Initial velocity: 1–6 px/sec (converted to px/frame)
    const speed = (Math.random() * 2.5 + 0.5);
    const goldenAngle = 2.3999632; // radians (≈ 137.5°)
    const angle = (index * goldenAngle) % (2 * Math.PI);
    
    const vx = Math.cos(angle) * speed;
    const vy = Math.sin(angle) * speed;

    blob.style.width = `${baseSize}px`;
    blob.style.height = `${baseSize}px`;
    blob.style.left = `${x}px`;
    blob.style.top = `${y}px`;
    blob.style.filter = `blur(${baseBlur}px)`;

    // Create unique keyframes for each blob
    const animName = `pulseBlob${index}`;
    const pulseDuration = Math.random() * 7 + 3; // 3s–10s

    styleSheet.sheet.insertRule(`
      @keyframes ${animName} {
        0%, 100% {
          width: ${baseSize}px;
          height: ${baseSize}px;
          filter: blur(${baseBlur}px);
        }
        50% {
          width: ${maxSize}px;
          height: ${maxSize}px;
          filter: blur(${maxBlur}px);
        }
      }
    `, styleSheet.sheet.cssRules.length);

    blob.style.animation = `${animName} ${pulseDuration}s ease-in-out infinite`;

    blobData.push({ el: blob, x, y, vx, vy, width: baseSize, height: baseSize });
  });

  function animate() {
    let frameCount = 0;
    blobData.forEach((b, index) => {
      b.x += b.vx;
      b.y += b.vy;

      if (b.x <= 0 || b.x + b.width >= window.innerWidth) {
        b.vx *= -1;
        b.x = Math.max(0, Math.min(window.innerWidth - b.width, b.x));
      }

      if (b.y <= 0 || b.y + b.height >= window.innerHeight) {
        b.vy *= -1;
        b.y = Math.max(0, Math.min(window.innerHeight - b.height, b.y));
      }
      frameCount++;
      const driftX = Math.sin(frameCount / 300 + index) * 0.25;
      const driftY = Math.cos(frameCount / 300 + index) * 0.25;

      b.el.style.left = `${b.x + driftX}px`;
      b.el.style.top  = `${b.y + driftY}px`;
    });

    requestAnimationFrame(animate);
  }

  animate();
});
