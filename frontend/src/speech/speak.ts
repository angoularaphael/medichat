const VOICE_KEY = "eir_voice_enabled";

type SpeakHooks = {
  onStart?: () => void;
  onEnd?: () => void;
};

let generation = 0;
let keepAlive = 0;

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function voiceEnabled(): boolean {
  if (!canSpeak()) return false;
  const stored = localStorage.getItem(VOICE_KEY);
  if (stored === null) return true;
  return stored === "1";
}

export function setVoiceEnabled(on: boolean): void {
  localStorage.setItem(VOICE_KEY, on ? "1" : "0");
  if (!on) stopSpeaking();
}

export function welcomeText(name?: string | null): string {
  const who = name?.trim();
  const hello = who ? `Bonjour ${who}.` : "Bonjour.";
  return (
    `${hello} Ici EIR, la pharmacie de bord. ` +
    "Decris ce que tu ressens. " +
    "Je verifie ton profil, tes allergies et le stock avant de te repondre."
  );
}

export function stopSpeaking(): void {
  generation += 1;
  if (keepAlive) {
    window.clearInterval(keepAlive);
    keepAlive = 0;
  }
  if (canSpeak()) window.speechSynthesis.cancel();
}

export function primeSpeech(): void {
  if (!canSpeak() || !voiceEnabled()) return;
  window.speechSynthesis.resume();
}

function frenchVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((voice) => voice.lang.toLowerCase().startsWith("fr")) ?? null
  );
}

export function speak(text: string, hooks?: SpeakHooks): void {
  if (!canSpeak() || !voiceEnabled()) {
    hooks?.onEnd?.();
    return;
  }
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) {
    hooks?.onEnd?.();
    return;
  }
  const mine = generation + 1;
  generation = mine;
  if (keepAlive) {
    window.clearInterval(keepAlive);
    keepAlive = 0;
  }
  window.speechSynthesis.cancel();

  const start = () => {
    if (mine !== generation) return;
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "fr-FR";
    utterance.rate = 1;
    const voice = frenchVoice();
    if (voice) utterance.voice = voice;
    utterance.onstart = () => {
      if (mine !== generation) return;
      hooks?.onStart?.();
      keepAlive = window.setInterval(() => {
        if (!window.speechSynthesis.speaking) {
          window.clearInterval(keepAlive);
          keepAlive = 0;
          return;
        }
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
      }, 10000);
    };
    utterance.onend = () => {
      if (mine !== generation) return;
      if (keepAlive) {
        window.clearInterval(keepAlive);
        keepAlive = 0;
      }
      hooks?.onEnd?.();
    };
    utterance.onerror = () => {
      if (mine !== generation) return;
      hooks?.onEnd?.();
    };
    window.speechSynthesis.speak(utterance);
  };

  if (window.speechSynthesis.getVoices().length > 0) {
    window.setTimeout(start, 60);
    return;
  }
  const onVoices = () => {
    window.speechSynthesis.removeEventListener("voiceschanged", onVoices);
    start();
  };
  window.speechSynthesis.addEventListener("voiceschanged", onVoices);
  window.speechSynthesis.getVoices();
}
