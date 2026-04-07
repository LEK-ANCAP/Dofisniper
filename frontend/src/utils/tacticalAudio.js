// Tactical Audio Subsystem (Web Audio API)
// Genera efectos de sonido militares sin necesidad de archivos externos.

let audioCtx = null;

function getContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

// 1. Clic Mecánico / Táctico (Interacciones de Interfaz)
export function playTacticalClick(volume = 0.05) {
  try {
    const ctx = getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    // Un "tick" seco y mecánico usando onda cuadrada rápida
    osc.type = 'square';
    osc.frequency.setValueAtTime(600, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(100, ctx.currentTime + 0.03);
    
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.03);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.03);
  } catch(e) {}
}

// 2. Alarma de Target Lock / Engage (Al lanzar disparo manual)
export function playEngageAlarm() {
  try {
    const ctx = getContext();
    
    // Tono 1
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sawtooth';
    osc1.frequency.setValueAtTime(400, ctx.currentTime);
    osc1.frequency.linearRampToValueAtTime(800, ctx.currentTime + 0.2);
    gain1.gain.setValueAtTime(0, ctx.currentTime);
    gain1.gain.linearRampToValueAtTime(0.1, ctx.currentTime + 0.05);
    gain1.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.2);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start();
    osc1.stop(ctx.currentTime + 0.2);

    // Tono 2 (Confirmación)
    setTimeout(() => {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = 'square';
        osc2.frequency.setValueAtTime(1200, ctx.currentTime);
        gain2.gain.setValueAtTime(0.1, ctx.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start();
        osc2.stop(ctx.currentTime + 0.1);
    }, 250);
  } catch(e) {}
}

// 3. Misión Exitosa (Ping de Sonar o Confirmación de Radio)
export function playMissionSuccess() {
  try {
    const ctx = getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = 'sine';
    // Sonar sweep ascendente
    osc.frequency.setValueAtTime(800, ctx.currentTime);
    osc.frequency.setValueAtTime(1600, ctx.currentTime + 0.1);
    
    gain.gain.setValueAtTime(0, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.15, ctx.currentTime + 0.05);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.0);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 1.0);
  } catch(e) {}
}

// 4. Falla Táctica / Misión Abortada (Buzzer de Peligro)
export function playMissionFail() {
  try {
    const ctx = getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = 'sawtooth';
    // Buzzer bajo y constante
    osc.frequency.setValueAtTime(150, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(100, ctx.currentTime + 0.4);
    
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    // Modulación para dar efecto vibratorio (distorsión ruda)
    const modulator = ctx.createOscillator();
    const modGain = ctx.createGain();
    modulator.type = 'square';
    modulator.frequency.value = 50; 
    modGain.gain.value = 50;
    modulator.connect(modGain);
    modGain.connect(osc.frequency);
    
    modulator.start();
    osc.start();
    modulator.stop(ctx.currentTime + 0.4);
    osc.stop(ctx.currentTime + 0.4);
  } catch(e) {}
}

// 5. Transmisión Morse (Mientras ocurre una ejecución prolongada)
let morseActive = 0;
let morseTimeout = null;
const morsePattern = [1, 1, 3, 1, 3, 1, 1, 1, 3, 3, 1, 1]; // dots and dashes (durations)
let morseIndex = 0;

export function startMorseTransmission() {
  if (morseActive === 0) {
    const ctx = getContext();
    function playNextSignal() {
      if (morseActive === 0) return;
      if (ctx.state === 'suspended') ctx.resume();
      
      const durationMultiplier = 45; // velocidad del morse en ms
      const currentSignal = morsePattern[morseIndex % morsePattern.length];
      const duration = (currentSignal * durationMultiplier) / 1000.0;
      
      try {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(800, ctx.currentTime); 
          
          gain.gain.setValueAtTime(0.04, ctx.currentTime); // Volumen más perceptible
          // Envolvente cuadrada para que suene como un switch
          gain.gain.setValueAtTime(0, ctx.currentTime + duration - 0.01);
          
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start();
          osc.stop(ctx.currentTime + duration);
      } catch(e) {}
      
      morseIndex++;
      const pauseDuration = durationMultiplier * 1.5; // Espacio de silencio
      morseTimeout = setTimeout(playNextSignal, (duration * 1000) + pauseDuration);
    }
    playNextSignal();
  }
  morseActive++;
}

export function stopMorseTransmission() {
  if (morseActive > 0) morseActive--;
  if (morseActive === 0 && morseTimeout) {
    clearTimeout(morseTimeout);
    morseTimeout = null;
  }
}
